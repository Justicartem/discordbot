import discord
import requests
import aiohttp
import os
import re
import gdown
from bs4 import BeautifulSoup
from tqdm import tqdm

# Configuración del bot
DISCORD_TOKEN = '' #Agregar aqui el ID de tu bot de discord :)
CHANNEL_ID = ""  # Agregar el ID en el que el bot trabajara
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    channel = client.get_channel(CHANNEL_ID)
    await channel.send('ez')
    print(f'Bot conectado como {client.user}')

async def download_file(url, file_name, message):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 1024
            progress_msg = await message.channel.send(f"Descargando {file_name}: 0.00%")
            with open(file_name, 'wb') as f, tqdm(
                total=total_size, unit='iB', unit_scale=True, desc=file_name, leave=False
            ) as bar:
                for chunk in response.content.iter_chunked(chunk_size):
                    f.write(chunk)
                    bar.update(len(chunk))
                    progress = (bar.n / total_size) * 100
                    speed = bar.n / (bar.format_dict["elapsed"] + 1e-6)
                    await progress_msg.edit(content=f"Descargando {file_name}: {progress:.2f}% a {speed:.2f} bytes/seg")
            await progress_msg.edit(content=f"Descarga completada: {file_name}")

def get_mediafire_direct_link(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    download_button = soup.find('a', {'id': 'downloadButton'})
    if download_button and 'href' in download_button.attrs:
        return download_button['href']
    return None

def extract_google_drive_file_id(url):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

def get_google_drive_file_info(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    title = soup.find('meta', {'property': 'og:title'})
    if title and 'content' in title.attrs:
        file_name = title['content']
        file_id = extract_google_drive_file_id(url)
        if file_id:
            return file_name, f'https://drive.google.com/uc?export=download&id={file_id}'
    return None, None

def get_mediafire_file_info(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    title = soup.find('meta', {'name': 'description'})
    if title and 'content' in title.attrs:
        file_name = title['content'].split(' - ')[0] + '.zip'
        download_button = soup.find('a', {'id': 'downloadButton'})
        if download_button and 'href' in download_button.attrs:
            return file_name, download_button['href']
    return None, None

def direct_download_link(url):
    if 'drive.google.com' in url:
        return get_google_drive_file_info(url)
    elif 'mediafire.com' in url:
        return get_mediafire_file_info(url)
    else:
        return None, None

def generate_valid_filename(file_name):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        file_name = file_name.replace(char, '_')
    return file_name

def download_from_google_drive(file_id, file_name):
    gdown.download(f'https://drive.google.com/uc?id={file_id}', file_name, quiet=False)

async def upload_file(channel, file_name):
    with open(file_name, 'rb') as f:
        progress_msg = await channel.send(f'Subiendo {file_name}...')
        async with channel.typing():
            message = await channel.send(file=discord.File(f, filename=file_name))
        await progress_msg.edit(content=f'Subida completa: {file_name}')
    os.remove(file_name)

@client.event
async def on_message(message):
    if message.author == client.user or message.channel.id != CHANNEL_ID:
        return

    if message.content.startswith('!descargar'):
        parts = message.content.split(' ')
        if len(parts) < 2:
            await message.channel.send('Por favor, proporciona un enlace después del comando !descargar.')
            return

        url = parts[1]
        file_name, direct_url = direct_download_link(url)

        if not file_name:
            file_name = generate_valid_filename(url)

        if direct_url and 'drive.google.com' in direct_url:
            file_id = extract_google_drive_file_id(url)
            file_name = generate_valid_filename(file_name or f'drive_file_{file_id}')
            download_from_google_drive(file_id, file_name)
            success = os.path.exists(file_name)
        elif direct_url and 'mediafire.com' in direct_url:
            success = await download_file(direct_url, file_name, message)
        else:
            await message.channel.send('URL no soportada o no se puede convertir a enlace directo.')
            return

        if success:
            await upload_file(message.channel, file_name)
        else:
            await message.channel.send('Error al descargar el archivo.')

client.run(DISCORD_TOKEN)
