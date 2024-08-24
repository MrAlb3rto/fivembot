import discord
from discord.ext import commands, tasks
from discord import ButtonStyle, Intents, ui
import json
import os
import asyncio

# Verifica que el archivo de configuración existe
if not os.path.isfile('config.json'):
    raise FileNotFoundError("El archivo 'config.json' no se encuentra en el directorio actual.")

# Leer la configuración desde el archivo config.json
with open('config.json') as config_file:
    config = json.load(config_file)

intents = Intents.default()
intents.message_content = True  # Necesario para leer contenido de mensajes
bot = commands.Bot(command_prefix="!", intents=intents)

# Leer configuraciones
TOKEN = config['TOKEN']
CHANNEL_ID = config['CHANNEL_ID']
GUILD_ID = config['GUILD_ID']

# Archivos para guardar el estado
INVENTORY_FILE = 'inventario.json'
HISTORY_FILE = 'historial.json'

# Cargar inventario desde el archivo JSON, inicializar si está vacío o da error
try:
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, 'r') as f:
            inventario = json.load(f)
            if not isinstance(inventario, dict):  # Asegurar que el inventario es un diccionario
                inventario = {"pipa": 7, "sns": 9, "micro": 17, "subfusil": 3, "minisubfusil": 0}
    else:
        inventario = {"pipa": 7, "sns": 9, "micro": 17, "subfusil": 3, "minisubfusil": 0}
except (json.JSONDecodeError, ValueError):
    inventario = {"pipa": 7, "sns": 9, "micro": 17, "subfusil": 3, "minisubfusil": 0}

# Cargar historial desde el archivo JSON, inicializar si está vacío o da error
try:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            historial = json.load(f)
            if not isinstance(historial, list):  # Asegurar que el historial es una lista
                historial = []
    else:
        historial = []
except (json.JSONDecodeError, ValueError):
    historial = []

message_id = None
history_message_id = None

# Definir los botones globalmente
button_row = [
    ui.Button(label="Añadir", style=ButtonStyle.green, custom_id="add_item"),
    ui.Button(label="Restar", style=ButtonStyle.red, custom_id="remove_item"),
    ui.Button(label="Ver Inventario", style=ButtonStyle.grey, custom_id="view_inventory"),
    ui.Button(label="Ver Historial", style=ButtonStyle.grey, custom_id="view_history"),
    ui.Button(label="Vaciar Chat", style=ButtonStyle.red, custom_id="clear_chat")  # Botón para vaciar el chat
]

# Crear un botón de selección para cada arma
def create_item_buttons(action):
    return [
        ui.Button(label="pipa", style=ButtonStyle.green if action == "add" else ButtonStyle.red, custom_id=f"{action}_pipa"),
        ui.Button(label="sns", style=ButtonStyle.green if action == "add" else ButtonStyle.red, custom_id=f"{action}_sns"),
        ui.Button(label="micro", style=ButtonStyle.green if action == "add" else ButtonStyle.red, custom_id=f"{action}_micro"),
        ui.Button(label="subfusil", style=ButtonStyle.green if action == "add" else ButtonStyle.red, custom_id=f"{action}_subfusil"),
        ui.Button(label="minisubfusil", style=ButtonStyle.green if action == "add" else ButtonStyle.red, custom_id=f"{action}_minisubfusil")
    ]

@bot.event
async def on_ready():
    global message_id
    print(f"Bot {bot.user} is ready and online!")

    # Obtén el canal por su ID
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        guild = bot.get_guild(GUILD_ID)
        server_icon_url = guild.icon.url if guild else None

        # Crear la vista y añadir los botones
        view = ui.View()
        for button in button_row:
            view.add_item(button)

        # Crear el embed inicial
        embed = discord.Embed(
            title="Inventario de Objetos",
            description="Gestiona los objetos utilizando los botones de abajo.\n\nSi ves algún mensaje de interacción fallida o error, verifica si la acción se realizó correctamente. Si tienes problemas, pregunta a Albertito.",
            color=discord.Color.blue()
        )
        if server_icon_url:
            embed.set_thumbnail(url=server_icon_url)

        # Enviar el mensaje inicial y guardar el ID
        message = await channel.send(embed=embed, view=view)
        message_id = message.id

        # Iniciar las tareas
        check_main_message.start()
        check_duplicate_messages.start()
    else:
        print(f"No se pudo encontrar el canal con ID {CHANNEL_ID}")

@tasks.loop(seconds=3)
async def check_main_message():
    global message_id
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        try:
            # Intenta obtener el mensaje principal
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            # Si el mensaje no se encuentra, envíalo de nuevo
            guild = bot.get_guild(GUILD_ID)
            server_icon_url = guild.icon.url if guild else None

            view = ui.View()
            for button in button_row:
                view.add_item(button)

            embed = discord.Embed(
                title="Inventario de Objetos",
                description="Gestiona los objetos utilizando los botones de abajo.\n\nSi ves algún mensaje de interacción fallida o error, verifica si la acción se realizó correctamente. Si tienes problemas, pregunta a Albertito.",
                color=discord.Color.blue()
            )
            if server_icon_url:
                embed.set_thumbnail(url=server_icon_url)

            # Enviar el mensaje principal de nuevo
            message = await channel.send(embed=embed, view=view)
            message_id = message.id  # Actualizar el ID del mensaje principal

@tasks.loop(seconds=15)
async def check_duplicate_messages():
    global message_id
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        messages = await channel.history(limit=100).flatten()
        main_message_count = sum(1 for msg in messages if msg.author == bot.user and msg.id == message_id)

        # Si hay más de una instancia del mensaje principal, eliminar los duplicados
        for msg in messages:
            if msg.author == bot.user and msg.id != message_id:
                await msg.delete()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    global message_id, history_message_id
    user = interaction.user.mention
    custom_id = interaction.data["custom_id"]

    channel = interaction.channel  # Obtener el canal donde ocurrió la interacción

    # Crear un nuevo embed para actualizar el mensaje
    def create_embed(title, description):
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        guild = bot.get_guild(GUILD_ID)
        server_icon_url = guild.icon.url if guild else None
        if server_icon_url:
            embed.set_thumbnail(url=server_icon_url)
        return embed

    try:
        if custom_id in ["remove_item", "add_item"]:
            action = "remove" if custom_id == "remove_item" else "add"

            # Crear botones para seleccionar el item a añadir o restar
            action_buttons = create_item_buttons(action)
            view = ui.View()
            for button in action_buttons:
                view.add_item(button)

            response_embed = discord.Embed(title=f"Selecciona el item que quieres {action}", color=discord.Color.blue())
            # Enviar el mensaje de selección
            response_message = await channel.send(embed=response_embed, view=view)

            # Esperar a que el usuario haga una selección
            try:
                selection = await bot.wait_for('interaction', timeout=60.0, check=lambda i: i.channel == channel and i.user == interaction.user)
                item_action, item = selection.data["custom_id"].split("_")
                if item in inventario:
                    if item_action == "remove":
                        inventario[item] -= 1
                        response_message_text = f"{user} ha quitado 1 {item}. Total: {inventario[item]}"
                    elif item_action == "add":
                        inventario[item] += 1
                        response_message_text = f"{user} ha añadido 1 {item}. Total: {inventario[item]}"

                    # Añadir al historial
                    historial.append(response_message_text)

                    # Crear un nuevo embed para actualizar el mensaje
                    description = f"Gestiona los objetos utilizando los botones de abajo.\n\n{response_message_text}"
                    embed = create_embed("Inventario de Objetos", description)

                    # Enviar el mensaje actualizado
                    new_message = await channel.send(embed=embed, view=ui.View().add_item(button_row[0]).add_item(button_row[1]).add_item(button_row[2]).add_item(button_row[3]).add_item(button_row[4]))
                    message_id = new_message.id

                    # Eliminar mensajes antiguos
                    async for msg in channel.history(limit=100):
                        if msg.id != message_id and msg.author == bot.user:
                            await msg.delete()
                    
                    # Eliminar el mensaje de selección
                    await response_message.delete()
                else:
                    await selection.response.send_message("Item no válido", ephemeral=True)
            except asyncio.TimeoutError:
                await response_message.delete()
                await interaction.response.send_message("Tiempo de espera agotado. Por favor, intenta de nuevo.", ephemeral=True)

        elif custom_id == "view_inventory":
            # Crear el embed para mostrar el inventario
            description = "\n".join(f"{item}: {quantity}" for item, quantity in inventario.items())
            embed = create_embed("Inventario", description)

            # Enviar el mensaje del inventario
            response_message = await channel.send(embed=embed)
            await asyncio.sleep(3)  # Esperar 3 segundos antes de eliminar el mensaje
            await response_message.delete()

        elif custom_id == "view_history":
            # Crear el embed para mostrar el historial
            description = "\n".join(historial) if historial else "El historial está vacío."
            embed = create_embed("Historial", description)

            # Enviar el mensaje del historial
            response_message = await channel.send(embed=embed)
            await asyncio.sleep(3)  # Esperar 3 segundos antes de eliminar el mensaje
            await response_message.delete()

        elif custom_id == "clear_chat":
            async for message in channel.history(limit=100):
                if message.author == bot.user and message.id != message_id:
                    await message.delete()

            # Enviar el mensaje principal de nuevo
            guild = bot.get_guild(GUILD_ID)
            server_icon_url = guild.icon.url if guild else None

            view = ui.View()
            for button in button_row:
                view.add_item(button)

            embed = discord.Embed(
                title="Inventario de Objetos",
                description="Gestiona los objetos utilizando los botones de abajo.\n\nSi ves algún mensaje de interacción fallida o error, verifica si la acción se realizó correctamente. Si tienes problemas, pregunta a Albertito.",
                color=discord.Color.blue()
            )
            if server_icon_url:
                embed.set_thumbnail(url=server_icon_url)

            new_message = await channel.send(embed=embed, view=view)
            message_id = new_message.id

        # Guardar inventario y historial en archivos JSON
        with open(INVENTORY_FILE, 'w') as f:
            json.dump(inventario, f, indent=4)

        with open(HISTORY_FILE, 'w') as f:
            json.dump(historial, f, indent=4)

    except discord.DiscordException as e:
        print(f"Error handling interaction: {e}")
        await interaction.response.send_message("Hubo un error al procesar la interacción. Inténtalo de nuevo.", ephemeral=True)

bot.run(TOKEN)
