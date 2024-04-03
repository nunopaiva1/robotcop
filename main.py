from code import interact
from select import select
from unicodedata import name
import nextcord
from nextcord import ButtonStyle
from nextcord.ext import commands, tasks
from nextcord.ui import View, Button
import requests
import json
import math
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.base import JobLookupError
import openai
import os
import datetime
from datetime import timedelta
import re
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
openai.api_key = os.getenv('OPENAI_TOKEN')

#from chatterbot import ChatBot
#from chatterbot.trainers import ListTrainer

# List of conversations
conversations = [
    ["Thanks", "You're welcome!"],
    ["Thank you.", "You're welcome!"],
    ["Thanks a lot.", "It's my pleasure!"],
    ["Thank you so much!", "I'm happy to help!"],
    ["Thanks for your assistance.", "Anytime!"],
    ["Appreciate it!", "No problem!"],
    ["Thanks a bunch.", "Glad I could assist!"],
    ["Thank you very much.", "It was my pleasure!"],
    ["Thanks a million.", "Always here to help!"],
    ["ty", "np!"]
]

# Create a new ChatBot instance
#chatbot = ChatBot('MyBot')

# Create a new ListTrainer for the chatbot
#trainer = ListTrainer(chatbot)

# Train the chatbot with the list of conversations
#for conversation in conversations:
#   trainer.train(conversation)

#openai.api_key = "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"

intents = nextcord.Intents.all()
client = commands.Bot(command_prefix = '!', intents=intents)

client.load_extension('coc')

#---------------********************-------------------
#                 ASYNCIO SCHEDULER
#---------------********************-------------------

# Initialize the scheduler
scheduler = AsyncIOScheduler(jobstores={'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')})
# Start the scheduler
scheduler.start()
def save_jobs():
    scheduler.print_jobs(out=open('jobs.txt', 'w'))

def load_jobs():
    # Check if the job store with the "default" alias already exists
    if 'default' not in scheduler._jobstores:
        scheduler.add_jobstore(SQLAlchemyJobStore(url='sqlite:///jobs.sqlite'))

load_jobs()

def delete_job(job_id):
    try:
        scheduler.remove_job(job_id)
        print(f"Job with ID {job_id} successfully deleted.")
    except JobLookupError:
        print(f"Job with ID {job_id} not found.")

async def send_reminder(user_id, reminder):
    print(f"Sending reminder: {reminder} to user with ID {user_id}")
    try:
        user = await client.fetch_user(user_id)
        if user:
            await user.send(f"Reminder: {reminder}")

            # Load existing reminders
            reminders = load_data('reminders')

            reminders = [r for r in reminders if r['reminder'] != reminder]

            # Save the updated reminders
            save_data('reminders', reminders)

    except Exception as e:
        logging.error(f"Error sending reminder: {e}")
    
    save_jobs()

async def schedule_reminder(user_id, reminder):
    print(f"Reminder scheduled. Sending now...")
    await send_reminder(user_id, reminder)

#---------------********************-------------------
#                LOADING JSON FILES
#---------------********************-------------------

data_folder = 'data'

# Load data from file
def load_gmData(file_name):
    file_path = os.path.join(data_folder, f'{file_name}.json')
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        # If the file doesn't exist, return a default value or initialize with default data
        return {}
    except json.decoder.JSONDecodeError:
        # If the file is empty or contains invalid JSON, return a default value or initialize with default data
        return {}

# Function to save data to a JSON file
def save_gmData(file_name, data):
    file_path = os.path.join(data_folder, f'{file_name}.json')
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def load_data(file_name):
    file_path = os.path.join(data_folder, f'{file_name}.json')
    
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            for item in data:
                if 'start_time' in item:
                    item['start_time'] = datetime.datetime.fromisoformat(item['start_time'])
    except (FileNotFoundError, json.JSONDecodeError):
        # Handle the case where the file doesn't exist or is empty
        data = []

    return data

def default_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def save_data(file_name, data):
    file_path = os.path.join(data_folder, f'{file_name}.json')

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2, default=default_serializer)

#---------------********************-------------------
#                    OPEN WEATHER
#---------------********************-------------------

api_key = os.getenv('WEATHER_TOKEN')

def get_weather(location):
    city_id = location
    url = f'http://api.openweathermap.org/data/2.5/weather?id={city_id}&appid={api_key}'
    response = requests.get(url)
    weather_data = response.json()
    return weather_data

# Kelvin to Celsius conversion function
def kelvin_to_celsius(kelvin):
    return kelvin - 273.15

def get_weather_emoji(weather_conditions):
    for condition in weather_conditions:
        main_condition = condition.get('main', '').lower()

        if 'clear' in main_condition:
            return '☀️'  # Sunny
        elif 'rain' in main_condition:
            return '🌧️'  # Rainy
        elif 'cloud' in main_condition:
            return '☁️'  # Cloudy
        # Add more conditions as needed

    return '❓'  # Default emoji for unknown conditions

# Extracting relevant information and converting to Celsius
def get_temp_summary(location_weather, location_name):
    #temp_max = kelvin_to_celsius(location_weather['main']['temp_max'])
    temp_min = kelvin_to_celsius(location_weather['main']['temp_min'])
    
    weather_conditions = location_weather.get('weather', [])
    weather_emoji = get_weather_emoji(weather_conditions)

    return f'{weather_emoji} {temp_min:.0f}°C'

#---------------********************-------------------
#                     JOKESTERS
#---------------********************-------------------

jokeurl = "https://v2.jokeapi.dev/joke/Any"
joke_response = requests.get(jokeurl)

#function
def get_joke():
    joke_response = requests.get(jokeurl)
    joke_data = json.loads(joke_response.text)
    return joke_data

#---------------********************-------------------
#              RANDOM NUMBERS MESSAGES
#---------------********************-------------------

inspire_url = "https://api.quotable.io/random"

# Function
def get_quote():
    try:
        randomQuote_response = requests.get(inspire_url)
        randomQuote_response.raise_for_status()  # Raises an HTTPError for bad responses
        quote_data = randomQuote_response.json()
        return quote_data["content"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching quote: {e}")
        return None

#---------------********************-------------------
#                  RANDOM MESSAGES
#---------------********************-------------------

randommsgurl = "https://www.boredapi.com/api/activity"
randommsg = requests.get(randommsgurl)

#function
def get_randommsg():
    randommsg = requests.get(randommsgurl)
    randommsg_data = json.loads(randommsg.text)
    return randommsg_data

#---------------********************-------------------
#                   TORRENT MAIN
#---------------********************-------------------

torrenturl = "http://torrents-csv.com/service/search?q={query}&size={num_results}&page={page}"

# Function to get torrent data from the API
def get_torrents(query, num_results=5, page=1):
    url = torrenturl.format(query=query, num_results=num_results, page=page)
    torrent_response = requests.get(url)
    torrent_data = json.loads(torrent_response.text)
    return torrent_data

# Function to create an embed message for a torrent
def create_torrent_embed(torrent, result_index):
    embed = nextcord.Embed(
        title=torrent['name'],
        description=f"Torrent Link: {torrent['infohash']} \n Seeders: {torrent['seeders']} | Leechers: {torrent['leechers']}",
        color=0xE69138  # You can change the color as desired
    )
    # Set a different color for the first result
    if result_index == 0:
        embed.color = 0x6AA84F  # Change this color to something else

    size_formatted = format_size(torrent['size_bytes'])
    embed.set_footer(text=size_formatted)

    return embed

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    size = round(size_bytes / p, 2)
    return f"{size} {size_name[i]}"

#------------------------- EVENTS -----------------------
@client.event
async def on_ready():
    print("______pi piri pu______")
    print("READY!")
    print("______pi piri pu______")

@client.event
async def on_member_join(member):
    channel = client.get_channel(419573473380270082)
    await channel.send(f"**Another one bites the dust. Farewell, {member.name}!** :nunuL:")

@client.event
async def on_member_remove(member):
    channel = client.get_channel(419573473380270082)
    await channel.send(f"**Another one bites the dust. Farewell, {member.name}!**")

@client.event
async def on_message(message):
    keywords_delete = ["retard", "nigg", "n1gg"]
    keywords_bad = ["caga", "caguei", "cago", "mija", "mijo", "mijei", "shit", "fuck"]
    keywords_thanks = ["thanks", "tank u", "thank you", "tanks", "tanks you", "thank", "appreciate","ty", "obg", "bigad", "brigad"]

    if message.author == client.user:
        return  # Ignore messages from the bot itself

    if message.content.startswith(client.command_prefix):
        await client.process_commands(message)  # Process commands as usual

    elif any(keyword in message.content for keyword in keywords_delete):
        keyword = next((kw for kw in keywords_delete if kw in message.content), None)
        await message.delete()

    elif "joke" in message.content:
        joke_data = get_joke()
        if joke_data['type'] == 'single':
            await message.channel.send(joke_data['joke'])
        elif joke_data['type'] == 'twopart':
            await message.channel.send(joke_data['setup'])
            await message.channel.send(joke_data['delivery'])

    elif any(keyword in message.content for keyword in keywords_bad):
        keyword = next((kw for kw in keywords_bad if kw in message.content), None)
        random_data = get_randommsg()
        if keyword:
            response = f"{keyword} really? Why don't you {random_data['activity'].lower()} instead?"
            await message.channel.send(response)
    
    elif message.channel.id == 1194760253049425930:  # Replace with your actual channel ID
        history = await message.channel.history(limit=5).flatten()  # Adjust limit as needed

        # Concatenate previous messages with the current prompt
        prompt = "\n".join([msg.content for msg in history]) + "\n" + message.content

        try:
            # Use OpenAI API to generate response
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # You can use any GPT-3.5 model here
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract the response from the API's output
            bot_reply = response.choices[0].message['content']

            # Send the generated response back to the chat
            await message.channel.send(bot_reply)

        except Exception as e:
            print("Error:", e)
    #elif any(thankword in message.content for thankword in keywords_thanks):
        #await message.channel.send(chatbot.get_response(message.content))

#------------------------- COMMANDS -----------------------

#@client.command(name='c')
#async def chat(ctx, *, message):
    #await ctx.send(chatbot.get_response(message))

@client.command(brief="Search for torrents")
async def tor(ctx, *, query):
    num_results = 4  # Set the default number of results to 5

    try:
        torrent_data = get_torrents(query, num_results)
    except Exception as e:
        # Handle the error here, and send an error message to the user
        await ctx.send(f"Sorry brotherman. Goddammit... I was trying to get you some torrents but the API is busy or smth: {e}\n\n Maybe try later? 😅")
        return


    if not torrent_data:
        await ctx.send("Impressive. I found a total of 0 torrents for the given query. Maybe try a different thing?")
    else:
        for index, torrent in enumerate(torrent_data):
            embed = create_torrent_embed(torrent, index)
            await ctx.send(embed=embed)

@client.command()
async def clear(ctx, num_messages: int):
    # Check if the user has permission to manage messages
    if ctx.author.guild_permissions.manage_messages:
        # Delete the specified number of messages (including the clear command)
        deleted = await ctx.channel.purge(limit=num_messages + 1)
        response_message = await ctx.send(f"Deleted {len(deleted) - 1} messages.")
        # Delete the response message after 2 seconds
        await asyncio.sleep(2)
        await response_message.delete()
    else:
        await ctx.send("You don't have the necessary permissions to use this command.")

'''
@client.command()
async def bibi(ctx):
    # Get the user who invoked the command
    user = ctx.author

    # Create buttons with labels
    yes_button = Button(label="Yes!", style=ButtonStyle.blurple)
    no_button = Button(label="No", style=ButtonStyle.secondary)

    # Define the callback function for the "Yes" button
    async def yes_callback(interaction):
        await interaction.response.send_message("``Phew! I mean... yeah, GREAT! \n\n ✨Someone✨ gave me a letter with your name on it. \n It reads: 'Para o meu amor de hoje e sempre 🩷' \n \n Should I open it? (click 'open' hehe.)``")
        
        # Create a new "Continue" button for the next question
        continue_button = Button(label="Open", style=ButtonStyle.blurple)

        # Define the callback function for the "Continue" button
        async def continue_callback(interaction):
            await interaction.response.send_message("``OK! Great! Here goes: `` \n\n**Para:** A minha companheira e alma gémea, *misttinha*\n**De:** nuuunu\n\nOlá, meu amor! \n\nEspero que esta carta te encontre bem. Quero que saibas que este dia é muito importante e carrega imenso significado para mim. \n\nHá 2 anos atrás, deixaste um inocente e sortudo Mogegense partilhar a vida com a alma mais ✨ doce, justa, linda e maravilhosa ✨ que este mundo tem para oferecer! \n\nQuero lembrar-te que desde dia até hoje, o meu amor por ti só tem crescido. Cada vez que te olho, te toco, beijo ou te tenho junto de mim, sinto-me totalmente completo e seguro do que quero para o meu futuro. O **nosso** futuro! \n\nDeves ter alguém ao teu lado neste momento para te dar um abraço e um beicinho 🥹 \n\nAmo-te, princesa. Há 2 anos, hoje e para **sempre**. Parabéns!")
        
        # Create a new "Finish" button to end the conversation
        finish_button = Button(label="Finish", style=ButtonStyle.red)

        async def finish_callback(interaction):
            image_path = 'img.JPG'  # Replace with the actual image path
            image_file = nextcord.File(image_path)

            # Send a message with the image
            await interaction.response.send_message("``Ahm... I think that's all from me! \n\n Have a great day! \n\n\n OH WAIT! There's something else here! Have a fantastic rest of your day, alchemistta!``", file=image_file)

        # Assign the callbacks to the buttons
        continue_button.callback = continue_callback
        finish_button.callback = finish_callback

        # Create a new view for the next question
        next_question_view = nextcord.ui.View(timeout=180)
        next_question_view.add_item(continue_button)
        next_question_view.add_item(finish_button)

        # Edit the message to add the "Continue" and "Finish" buttons
        await interaction.message.edit(view=next_question_view)

    # Define the callback function for the "No" button
    async def no_callback(interaction):
        await interaction.response.send_message("Oh, that's alright. If you change your mind, just let me know. I'll be here!")

    # Assign the callbacks to the buttons
    yes_button.callback = yes_callback
    no_button.callback = no_callback

    # Create the initial view and add the buttons to it
    myview = nextcord.ui.View(timeout=180)
    myview.add_item(yes_button)
    myview.add_item(no_button)

    # Send a message to the user with the initial view (including the first set of buttons)
    await user.send(f"``Oh... aham. ✨ Hi! ✨ \n \n You're (*checking notes*) {user.name}, right?``", view=myview)
'''
'''
@client.command()
async def chat(ctx, *, message):
    try:
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=message,
            max_tokens=100  # You can adjust this based on your requirements
        )

        # Get the response from GPT-3
        bot_response = response.choices[0].text

        # Send the bot's response to the same channel
        await ctx.send(bot_response)
    except Exception as e:
        # Handle any errors that occur during the API call
        await ctx.send(f"An error occurred: {e}")
'''

# *--------------------------------------------------*
# ------------- GLOBAL VARIABLES ---------------------
# *--------------------------------------------------*

# Define a dictionary to store availability groups
availability_groups = {}
# Define a list to store information about open parties

@client.command()
async def avail(ctx, startTime, endTime):
    
    
    time_options = ["Early Afternoon", "Late Afternoon", "Night"]
    game_options = ["Fifa", "Overwatch", "Valorant", "Valheim", "Minecraft", "Other", "Any"]

    # Create a message with buttons for time options
    time_view = View()
    game_view = View()

    user_selections = {}
    availability_group = []  # List to store users who joined the group

    async def time_callback(interaction, selected_time):
        user_selections['Time'] = selected_time
        await interaction.response.send_message(content=f"You selected {selected_time}.")
        await interaction.message.edit(view=game_view)

    async def add_join_button(message):
        # Add a button for others to join
        join_button = Button(style=ButtonStyle.green, label="Join")
        join_button.callback = join_callback

        join_view = View()
        join_view.add_item(join_button)

        # Send a new message with the join button
        join_message = await message.channel.send("Click 'Join' to join this party!", view=join_view)

    async def game_callback(interaction, selected_game):
        current_time = datetime.datetime.now()
        
        if selected_game.lower() == "other":
            await interaction.response.send_message(content="What's the name of the game you want to play?")

            # Now, you need to wait for the user's response. You can use the wait_for method.
            def check(response):
                return response.author == interaction.user and response.channel == interaction.channel

            try:
                response = await client.wait_for("message", check=check, timeout=60)  # Adjust timeout as needed
                game_name = response.content
                user_selections['Game'] = game_name
                await interaction.followup.send(content=f"You selected '{game_name}'.")
            except asyncio.TimeoutError:
                await interaction.followup.send(content="Sorry, you took too long to respond.")
        else:
            user_selections['Game'] = selected_game
            await interaction.response.send_message(content=f"You selected {selected_game}.")

        #await ctx.channel.purge(limit=4)

        user_name = ctx.author.display_name
        party_title = f"{user_name}'s {user_selections['Game']} Party"

        current_date = datetime.date.today()
        
        start_time_raw = datetime.datetime.combine(current_date, datetime.time(int(startTime), 0))
        end_time_raw = datetime.datetime.combine(current_date, datetime.time(int(endTime), 0))

        if current_time > start_time_raw:
            tomorrow_date = current_date + datetime.timedelta(days=1)
            start_time = datetime.datetime.combine(tomorrow_date, datetime.time(int(startTime), 0))
            end_time = datetime.datetime.combine(tomorrow_date, datetime.time(int(endTime), 0))
        else:
            start_time = datetime.datetime.combine(current_date, datetime.time(int(startTime), 0))
            end_time = datetime.datetime.combine(current_date, datetime.time(int(endTime), 0))

            # Ensure end time is after start time
        if end_time <= start_time: 
            end_time += datetime.timedelta(days=1)

        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        start_discord_timestamp = f"<t:{start_timestamp}:R>"
        end_discord_timestamp = f"<t:{end_timestamp}:R>"

        # Create the initial embed
        embed = nextcord.Embed(title=party_title)

        # Add the "OP" field
        embed.add_field(name="OP", value=ctx.author.mention, inline=True)

        for key, value in user_selections.items():
            embed.add_field(name=key, value=value, inline=True)

        joined_users_field = ""
        for user in availability_group:
            joined_users_field += user.mention + "\n"
            
        if current_time < end_time:
            status = "Active"
        else:
            status = "Expired"
            
        embed.add_field(name="Start Time", value=start_discord_timestamp, inline=True)
        embed.add_field(name="End Time", value=end_discord_timestamp , inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Participants", value=joined_users_field, inline=True)

        # Send the initial embed
        message = await ctx.send(embed=embed, view=None)
        availability_group.append(ctx.author)  # Add the user to the group
        await add_join_button(message)

        # Create a new party and add it to the list of open parties
        party_info = {
            'party_title': party_title,
            'user_id': ctx.author.name,
            'time': start_time,
            'game': selected_game,
            'party_start_time': start_discord_timestamp,
            'end_time': end_discord_timestamp,
            'end_timeCode' : end_time,
            'isActive': True
        }
        open_parties = load_data('parties')
        open_parties.append(party_info)
        save_data('parties', open_parties)

    async def join_callback(interaction):
        selected_time = startTime
        selected_game = user_selections['Game']
        current_date = datetime.date.today()
        current_time = datetime.datetime.now()

        open_parties = load_data('parties')

        for party in open_parties:
            end_time_code = datetime.datetime.fromisoformat(party['end_timeCode'])
            if current_time > end_time_code:
                print("current: ", current_date, " and end time: ", end_time_code)
                party['isActive'] = False
                open_parties.remove(party)
                await interaction.response.send_message(content="This party has expired!")
                return

            if party['isActive'] == False:
                return

        if interaction.user in availability_group:
         '''responses = [
                "You are already in the availability group, stop trying to break me 😡",
                "Aren't you part of this group already?",
                "Alright buddy, I'll assume it was a misclick. You're part of this group already!!",
                "Yo you're part of this group. Want to create a new one or what?"
            ]

            selected_response = random.choice(responses)    
            await interaction.user.send(selected_response)'''
         await ctx.send("You're already in the group mate.")
         return
        else:            
            availability_group.append(interaction.user)

            user_name = ctx.author.display_name
            party_title = f"{user_name}'s {user_selections['Game']} Party"

            current_date = datetime.date.today()
            
            start_time_raw = datetime.datetime.combine(current_date, datetime.time(int(startTime), 0))

            if current_time > start_time_raw:
                tomorrow_date = current_date + datetime.timedelta(days=1)
                start_time = datetime.datetime.combine(tomorrow_date, datetime.time(int(startTime), 0))
                end_time = datetime.datetime.combine(tomorrow_date, datetime.time(int(endTime), 0))
            else:
                start_time = datetime.datetime.combine(current_date, datetime.time(int(startTime), 0))
                end_time = datetime.datetime.combine(current_date, datetime.time(int(endTime), 0))

            start_timestamp = int(start_time.timestamp())
            end_timestamp = int(end_time.timestamp())
            start_discord_timestamp = f"<t:{start_timestamp}:R>"
            end_discord_timestamp = f"<t:{end_timestamp}:R>"

            embed = nextcord.Embed(title=party_title)

            # Add the "OP" field
            embed.add_field(name="OP", value=ctx.author.mention, inline=True)

            for key, value in user_selections.items():
                embed.add_field(name=key, value=value, inline=True)

            joined_users_field = ""
            for user in availability_group:
                joined_users_field += user.mention + "\n"
            
            if current_time < end_time:
                status = "Active"
            else:
                status = "Expired"

            embed.add_field(name="Start Time", value=start_discord_timestamp, inline=True)
            embed.add_field(name="End Time", value=end_discord_timestamp , inline=True)
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Participants", value=joined_users_field, inline=True)

            #await ctx.channel.purge(limit=2)
            await interaction.response.send_message(content=f"{interaction.user.mention} joined the group.")
            message = await ctx.send(embed=embed)
            await add_join_button(message)

    '''for option in time_options:
        button = Button(style=ButtonStyle.primary, label=option)
        button.callback = lambda i, selected_time=option: time_callback(i, selected_time)
        time_view.add_item(button)'''

    for option in game_options:
        button = Button(style=ButtonStyle.primary, label=option)
        button.callback = lambda i, selected_game=option: game_callback(i, selected_game)
        game_view.add_item(button)

    message = await ctx.send("Please select a game:", view=game_view)

@client.command()
async def parties(ctx):
    current_time = datetime.datetime.now()

    open_parties = load_data('parties')

    if not open_parties:
        await ctx.send("There are no open parties at the moment. Create one with **!avail start_time(Hour) end_time(Hour)**")
    else:
        await ctx.send("**Open Parties:**\n\n")
        for party in open_parties:
            # Convert party['end_timeCode'] to a datetime object
            end_time_code = datetime.datetime.fromisoformat(party['end_timeCode'])

            if current_time > end_time_code:
                open_parties.remove(party)
                party['isActive'] = False
            else: 
                await ctx.send(f"Title: {party['party_title']}\nStarting Time: {party['party_start_time']}\nEnding Time: {party['end_time']}\n\n")

@client.command(name='remind')
async def remind(ctx, time, *, reminder):
    # Parse the time input using regular expressions
    time_regex = re.compile(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
    match = time_regex.match(time)

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    total_seconds = hours * 3600 + minutes * 60 + seconds

    await ctx.send(f"Okay, I will remind you in {time}.")

    reminders = load_data('reminders')

    reminders.append({
        'user_id': ctx.author.id,
        'reminder': reminder,
        'time': total_seconds,
        'start_time': datetime.datetime.now().isoformat(),
    })

    save_data('reminders', reminders)

    user_id = ctx.author.id

    # Save the job after scheduling it
    scheduler.add_job(
        schedule_reminder,
        args=[user_id, reminder],
        id=reminder,
        trigger='date',
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=total_seconds)
    )

    save_jobs()

@client.command(name='remindat')
async def remind_at(ctx, time, *, reminder):
    # Parse the time input using a regular expression
    time_regex = re.compile(r'(\d{1,2}):(\d{2})([ap]m)?')
    match = time_regex.match(time)

    if not match:
        await ctx.send("Invalid time format. Please use HH:mm or HH:mmam/pm.")
        return

    hour = int(match.group(1))
    minute = int(match.group(2))
    am_pm = match.group(3)

    if am_pm and am_pm.lower() == 'pm' and hour < 12:
        hour += 12
    elif am_pm and am_pm.lower() == 'am' and hour == 12:
        hour = 0

    now = datetime.datetime.now()
    reminder_time = datetime.datetime(now.year, now.month, now.day, hour, minute)

    # Calculate the time difference until the specified time
    time_difference = (reminder_time - now).total_seconds()

    # If the specified time is in the past, set the date for tomorrow
    if reminder_time < now:
        reminder_time += timedelta(days=1)

    # Calculate the time difference until the specified time
    time_difference = (reminder_time - now).total_seconds()

    reminders = load_data('reminders')

    reminders.append({
        'user_id': ctx.author.id,
        'reminder': reminder,
        'time': time_difference,
        'start_time': now.isoformat()
    })

    save_data('reminders', reminders)

    user_id = ctx.author.id

    # Save the job after scheduling it
    scheduler.add_job(
        schedule_reminder,
        kwargs={'user_id': ctx.author.id, 'reminder': reminder},
        id=reminder,
        trigger='date',
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=time_difference)
    )
    

    print(f"Reminder job scheduled for user ID {user_id}, reminder: {reminder}, time difference: {time_difference}")

    save_jobs()

    print("Jobs saved.")
    await ctx.send(f"Okay, I will remind you at {hour:02}:{minute:02}.")

@client.command(name='relist')
async def relist(ctx):
    embed = nextcord.Embed(title='Reminder List', color=0x00ff00)

    reminders = load_data('reminders')

    sorted_reminders = sorted(reminders, key=lambda x: x['time'] - (datetime.datetime.now() - (datetime.datetime.fromisoformat(x['start_time']) if 'start_time' in x and isinstance(x['start_time'], str) else datetime.datetime.now())).total_seconds())

    for index, reminder in enumerate(sorted_reminders, start=1):
        user = client.get_user(reminder['user_id'])
        remaining_time = reminder['time'] - (datetime.datetime.now() - reminder['start_time']).total_seconds()
        remaining_time_str = str(timedelta(seconds=max(0, round(remaining_time))))

        embed.add_field(
            name=f"Reminder {index} - {user.name}#{user.discriminator}",
            value=f"Time Remaining: {remaining_time_str}\nReminder: {reminder['reminder']}",
            inline=False
        )

    await ctx.send(embed=embed)

@client.command(name='gm')
async def dailytracker(ctx):

    # Get today's date and day of the week
    now = datetime.datetime.now()
    formatted_date = now.strftime('%A, %B %d, %Y')

    # Load reminders for the specific user and date
    reminders = load_data('reminders')

    user_reminders = [
        remi for remi in reminders
        if (
            remi['user_id'] == ctx.author.id
        )
    ]

    braga_weather = get_weather('2742032')
    viana_weather = get_weather('2732773')
    vila_real_weather = get_weather('2732438')

    # Create temperature summaries
    braga_temp_summary = get_temp_summary(braga_weather, 'Braga')
    viana_temp_summary = get_temp_summary(viana_weather, 'Viana')
    vila_real_temp_summary = get_temp_summary(vila_real_weather, 'Vila Real')

    quote_message = get_quote()

    embed = nextcord.Embed(
        title=f'Hello, {ctx.author.name}!',
        description=f'Today is {formatted_date}\n\nQuote: {quote_message}',
        #description=f'Today is {formatted_date}\n\nQuote: ``Quotable temporarily down :Sadge:``',
        color=0x0099ff
    )

    embed.add_field(name='Braga', value=f'{braga_temp_summary}', inline=True)
    embed.add_field(name='Viana do Castelo', value=f'{viana_temp_summary}', inline=True)
    embed.add_field(name='Vila Real', value=f'{vila_real_temp_summary}', inline=True)

    # Calculate the time at which each reminder will happen and format the reminders
    formatted_reminders = [
        f"- {reminder['reminder'].capitalize()} at {datetime.datetime.strftime(reminder['start_time'] + datetime.timedelta(seconds=reminder['time']), '%H:%M')}"
        for reminder in sorted(user_reminders, key=lambda x: x['time'], reverse=False)
    ]

    # Add the reminders to the embed
    if formatted_reminders:
        reminder_list = "\n".join(formatted_reminders)
        embed.add_field(name='Reminders for Today', value=reminder_list)
    else:
        embed.add_field(name='Reminders for Today', value='No reminders for today.')

    # Send the initial embed
    message = await ctx.send(embed=embed)
    return
 
@client.command(name='gmadd')
async def gmadd(ctx):
    # Get today's date and day of the week
    now = datetime.datetime.now()
    formatted_date = now.strftime('%A, %B %d, %Y')
    
        # Load reminders for the specific user and date
    reminders = load_data('reminders')

    user_reminders = [
        remi for remi in reminders
        if (
            remi['user_id'] == ctx.author.id
        )
    ]

    braga_weather = get_weather('2742032')
    viana_weather = get_weather('2732773')
    vila_real_weather = get_weather('2732438')

    # Create temperature summaries
    braga_temp_summary = get_temp_summary(braga_weather, 'Braga')
    viana_temp_summary = get_temp_summary(viana_weather, 'Viana')
    vila_real_temp_summary = get_temp_summary(vila_real_weather, 'Vila Real')


    quote_message = get_quote()
    quote = quote_message['content']

    embed = nextcord.Embed(
        title=f'Hello, {ctx.author.name}!',
        description=f'Today is {formatted_date}\n\nQuote: {quote}',
        #description=f'Today is {formatted_date}\n\nQuote: ``Quotable temporarily down :Sadge:``',
        color=0x0099ff
    )

    # Add weather information to the embed
    embed.add_field(name='Braga', value=f'{braga_temp_summary}', inline=True)
    embed.add_field(name='Viana do Castelo', value=f'{viana_temp_summary}', inline=True)
    embed.add_field(name='Vila Real', value=f'{vila_real_temp_summary}', inline=True)


    # Calculate the time at which each reminder will happen and format the reminders
    formatted_reminders = [
        f"- {reminder['reminder'].capitalize()} at {datetime.datetime.strftime(reminder['start_time'] + datetime.timedelta(seconds=reminder['time']), '%H:%M')}"
        for reminder in sorted(user_reminders, key=lambda x: x['time'], reverse=False)
    ]

    # Add the reminders to the embed
    if formatted_reminders:
        reminder_list = "\n".join(formatted_reminders)
        embed.add_field(name='Reminders for Today', value=reminder_list)
    else:
        embed.add_field(name='Reminders for Today', value='No reminders for today.')

    # Send the initial embed
    message = await ctx.send(embed=embed)

    # Send a chat message requesting daily tasks update
    await ctx.send("\n\nWrite your **Tasks** for today: (**none** to cancel) \n**e.g.** call someone at 15:00, reply to emails, another task at 18:30")

    # Listen for user's response
    def check(message):
        return message.author == ctx.message.author and message.channel == ctx.message.channel

    try:
        response = await client.wait_for('message', timeout=60.0, check=check)
        
        # Check if the user entered "none" to cancel editing
        if response.content.lower().strip() == 'none':
            await ctx.send("Editing canceled. No changes were made.")
            return

        user_tasks = [f"- {task.strip().capitalize()}" for task in response.content.split(',') if task.strip()]

        # Combine both reminders and tasks in a single field
        combined_list = formatted_reminders + user_tasks

        num_fields = len(embed.fields)
        # Update the field with combined reminders and tasks
        embed.set_field_at(num_fields - 1, name='Reminders for Today', value='\n'.join(combined_list))

        for task in user_tasks:
                # Check if "at" is present as a standalone word
                if f" {task.lower()} ".find(" at ") != -1:
                    # Split the task to extract the specified time
                    _, time_str = task.split("at", 1)
                    time = time_str.strip()

                    # Remove the "- " prefix and time from the task
                    reminder_text = task.replace("- ", "").replace(time, "").strip()

                    # Call the remindat command with the adjusted reminder text and time
                    await ctx.invoke(client.get_command("remindat"), reminder=reminder_text, time=time)

                else:
                    # If "at" is not present, set the time to 19:00
                    await ctx.invoke(client.get_command("remindat"), reminder=task.replace("- ", ""), time="19:00")

        # Edit the original message with the updated embed
        await message.edit(embed=embed)

    except asyncio.TimeoutError:
        await ctx.send('Time is up. If you have more tasks, please run the command again.')

@client.command(name='gmedit')
async def gmedit(ctx):
    
    # Load reminders for the specific user and date
    reminders = load_data('reminders')

    user_reminders = [
        remi for remi in reminders
        if (
            remi['user_id'] == ctx.author.id
        )
    ]
    
    if user_reminders:
        reminder_list = [f"{i}. {reminder['reminder']} at {datetime.datetime.strftime(reminder['start_time'] + datetime.timedelta(seconds=reminder['time']), '%H:%M')}" for i, reminder in enumerate(user_reminders)]
        reminder_interface = "\n".join(reminder_list)
        reminder_interface += "\n\nTo edit or remove a reminder, reply with the index number (e.g., 'edit 2' or 'remove 1')."

        await ctx.send(reminder_interface)

        def check_edit_remove(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            edit_remove_response = await client.wait_for('message', timeout=60.0, check=check_edit_remove)
            edit_remove_command = edit_remove_response.content.lower().split()[0]
            index = int(edit_remove_response.content.lower().split()[1]) - 1 if len(edit_remove_response.content.split()) > 1 else None

            if edit_remove_command == 'edit' and index is not None and 0 <= index < len(user_reminders):
                # Show only the selected reminder for editing
                selected_reminder = user_reminders[index]
                reminder_to_edit = f"{index + 1}. {selected_reminder['reminder']} at {datetime.datetime.strftime(selected_reminder['start_time'] + datetime.timedelta(seconds=selected_reminder['time']), '%H:%M')}"
                reminder_to_edit += "\n\nPlease provide the new reminder and/or time."

                await ctx.send(reminder_to_edit)

                # Now wait for the user's input
                try:
                    user_input_response = await client.wait_for('message', timeout=60.0, check=check_edit_remove)
                    new_reminder_text = user_input_response.content
                    new_time = "19:00"  # Default time if not provided by the user
                    if 'at' in new_reminder_text.lower():
                        new_time = new_reminder_text.split('at')[-1].strip()

                    # Delete the old reminder
                    removed_reminder = user_reminders.pop(index)

                    # Update the reminders list and save to the JSON file
                    reminders = [rem for rem in reminders if rem != removed_reminder]
                    save_data('reminders', reminders)

                    # Create the new reminder
                    await ctx.invoke(client.get_command("remindat"), reminder=new_reminder_text, time=new_time)

                    await ctx.send("Reminder updated and old one deleted!")

                except asyncio.TimeoutError:
                    await ctx.send("Time is up. If you want to edit or remove a reminder, please run the command again.")

            elif edit_remove_command == 'remove' and index is not None and 0 <= index < len(user_reminders):
                # Handle remove logic
                removed_reminder = user_reminders[index]
                user_reminders.remove(removed_reminder)

                print(f"IM HERE: {removed_reminder['reminder']}")

                all_jobs = scheduler.get_jobs()
                print("All Jobs in Scheduler:")
                for job in all_jobs:
                    print(job.id)
                    if job.id == removed_reminder['reminder']:
                        delete_job(removed_reminder['reminder'])
                        print(f"deleted: {job.id}")

                save_jobs()

                # Update the reminders list and save to the JSON file
                reminders = [rem for rem in reminders if rem != removed_reminder]
                save_data('reminders', reminders)

                await ctx.send(f"Removed reminder {index + 1}: {removed_reminder['reminder']}")

            else:
                await ctx.send("Invalid edit/remove command or index.")

        except asyncio.TimeoutError:
            await ctx.send("Time is up. If you want to edit or remove a reminder, please run the command again.")

    else:
        await ctx.send("No reminders or tasks to edit or remove.")

@client.command(name='jobs')
async def jobs(ctx):
    delete_job("Final test at")

    all_jobs = scheduler.get_jobs()
    print("All Jobs in Scheduler:")
    for job in all_jobs:
        print(job.id)

    save_jobs()

client.run(TOKEN)

#remindat @person
#contador quantas vezes o rook diz qual é este mapa?!


