import discord
from discord.ext import commands
from PIL import Image
import requests
from io import BytesIO
import os

# --- Configuración del Bot ---
# Reemplaza con tu token REAL de bot de Discord
# ¡Mantén este token en secreto!
TOKEN = TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Define a dictionary with the paths to your overlay images.
# The keys (e.g., 'common', 'epic') must be in lowercase,
# as the bot converts user input to lowercase for matching.
# Ensure these image files are in the same directory as your bot.py script.
OVERLAYS = {
    'rare': 'common_overlay.png',
    'epic': 'epic_overlay.png',
    'legendary': 'legendary_overlay.png',
    'common': 'rare_overlay.png'
}

# Configure Discord Intents. This is essential for the bot to read message content.
# Make sure "Message Content Intent" is enabled in your bot's settings
# on the Discord Developer Portal.
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

# Initialize the bot with a command prefix.
# Users will type '!' before a command, e.g., '!overlay common'.
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Bot Events ---
@bot.event
async def on_ready():
    """Executed when the bot successfully connects to Discord."""
    print(f'{bot.user.name} has connected to Discord!')
    print("Available overlay options:", ", ".join(OVERLAYS.keys()))
    print("To use: !overlay <option> (and attach an image to your message)")

# --- Bot Commands ---
@bot.command(name='overlay', help='Applies an overlay to your attached image. Usage: !overlay <option> (attach an image)')
async def apply_overlay(ctx, option: str = None):
    """
    Command to apply a chosen overlay to a user-provided image.
    Requires an overlay option and an image attached to the message.
    """
    # 1. Check if an overlay option was provided.
    if option is None:
        await ctx.send(
            f"Please specify an overlay option. Available options are: "
            f"`{', '.join(OVERLAYS.keys())}`. For example: `!overlay common`"
        )
        return

    # Convert the user's option to lowercase for case-insensitive matching.
    option = option.lower()

    # 2. Validate the provided overlay option.
    if option not in OVERLAYS:
        await ctx.send(
            f"Invalid overlay option. Available options are: "
            f"`{', '.join(OVERLAYS.keys())}`."
        )
        return

    # 3. Check if an image was attached to the message.
    if not ctx.message.attachments:
        await ctx.send("Please attach an image to your message to apply the overlay.")
        return

    # Get the file path for the selected overlay.
    overlay_path = OVERLAYS[option]

    # 4. Verify that the overlay image file exists on the bot's server.
    if not os.path.exists(overlay_path):
        await ctx.send(f"Oops! The overlay file `{overlay_path}` wasn't found on the bot's server. Please ensure it's in the same folder as the bot script.")
        return

    # Process the first attached image (if multiple are attached).
    attachment = ctx.message.attachments[0]

    # 5. Check if the attached file is a compatible image type.
    if not any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
        await ctx.send("The attached file is not a compatible image (PNG, JPG, JPEG, GIF).")
        return

    try:
        # 6. Download the original image from Discord.
        response = requests.get(attachment.url)
        # Open the image and convert it to RGBA to ensure transparency compatibility.
        original_image = Image.open(BytesIO(response.content)).convert("RGBA")

        # 7. Load the overlay image from the local file.
        # Also convert it to RGBA to handle its own transparency.
        overlay_image = Image.open(overlay_path).convert("RGBA")

        # --- Overlay Resizing and Positioning Logic ---
        # The overlay image will always be resized to 828x1312 pixels.
        target_overlay_width = 828
        target_overlay_height = 1312

        # Resize the overlay to the fixed target dimensions using a high-quality resampling filter.
        overlay_image = overlay_image.resize((target_overlay_width, target_overlay_height), Image.Resampling.LANCZOS)

        # Define padding (margin) for positioning.
        padding = 0 # Set to 0 for no extra margin when centering. Adjust if needed.

        # Calculate the position to center the overlay on the original image.
        # Integer division (//) ensures whole pixel values.
        x_offset = (original_image.width - target_overlay_width) // 2
        y_offset = (original_image.height - target_overlay_height) // 2

        # Ensure offsets are not negative (if the original image is smaller than the overlay).
        # This will paste the top-left corner of the overlay at the calculated position,
        # effectively clipping the overlay if it's larger than the original image.
        x_offset = max(0, x_offset)
        y_offset = max(0, y_offset)

        # 8. Paste the overlay onto the original image.
        # The 'mask' argument is critical for correctly applying the overlay's transparency.
        original_image.paste(overlay_image, (x_offset, y_offset), overlay_image)

        # 9. Save the combined image to a memory buffer.
        # Saving as PNG preserves transparency and generally high quality.
        output_buffer = BytesIO()
        original_image.save(output_buffer, format="PNG")
        output_buffer.seek(0) # Move the cursor to the beginning of the buffer for Discord to read.

        # 10. Send the processed image back to the Discord channel.
        await ctx.reply(file=discord.File(output_buffer, filename=f"image_with_{option}_overlay.png"))

    except Exception as e:
        # Catch any unexpected errors during image processing and inform the user.
        await ctx.send(f"An error occurred while processing the image: `{e}`. Please try again later.")

# --- Bot Execution ---
# This line starts the bot and connects it to Discord.
bot.run(TOKEN)