from unicodedata import name
import nextcord
from nextcord.ext import commands
import json
import os
from datetime import date, datetime
import yt_dlp
import random
import itertools
import requests

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {"shows": []}

def load_jsonSTATS(file_path):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in file {file_path}: {e}")
    return {"participants": []}

def save_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

def parse_date(date_str):
    try:
        # Parse the user-provided date string
        current_year = datetime.now().year
        date_str_with_year = f"{date_str} {current_year}"
        date_object = datetime.strptime(date_str_with_year, "%d %b at %H %Y")
        
        # Convert the date to UNIX timestamp
        timestamp = int(date_object.timestamp())
        # Format as Discord timestamp
        discord_timestamp = f"<t:{timestamp}:R>"
        return discord_timestamp
    except ValueError:
        return None

def download_youtube_videos(video_links_file, output_folder):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp3',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Read video links from the file
        with open(video_links_file, 'r') as file:
            video_links = [line.strip() for line in file.readlines()]

        # Download each video
        for video_link in video_links:
            try:
                ydl.download([video_link])

            except Exception as e:
                (f"Error downloading {video_link}: {e}")

class COC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_show_message_id = None  # Initialize the attribute
    
    def get_points_by_position(self, position):
        if position == '1st':
            return 6
        elif position == '2nd':
            return 4
        elif position == '3rd':
            return 3
        elif position == '4th':
            return 1
        else:
            return 0
    #================================================
                    #ADMIN COMMANDS
    #================================================

    @commands.command(name='cocadd', brief="[Admin-Only] Create COC - Add theme and date")
    async def coc_create(self, ctx):
        if ctx.author.guild_permissions.administrator:
            json_file_path = 'data/cocshow.json'
            coc_info = load_json(json_file_path)

            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel

            if not coc_info["shows"]:
                await ctx.send("The cocinfo.json file is empty. What theme do you want for the show?")
                theme_message = await self.bot.wait_for('message', check=check)
                theme = theme_message.content

                await ctx.send("What date and time is the show? (e.g., 17 Oct at 22)")
                date_message = await self.bot.wait_for('message', check=check)
                date_str = date_message.content

                # Parse and format the date
                discord_timestamp = parse_date(date_str)

                if discord_timestamp:
                    show = {"theme": theme, "date": discord_timestamp, 'started': False, 'inProgress': False, "participants": []}
                    coc_info["shows"].append(show)
                    save_json(json_file_path, coc_info)
                    await ctx.send(f"Show theme set to: {theme} Date/Time: {discord_timestamp}")
                else:
                    await ctx.send("Invalid date format. Please use the format: 17 Oct at 22")

            else:
                await ctx.send("Do you want to add a new show? (yes/no)")
                create_new_message = await self.bot.wait_for('message', check=check)
                create_new_response = create_new_message.content.lower()

                if create_new_response == 'yes':
                    await ctx.send("What theme do you want for this one?")
                    theme_message = await self.bot.wait_for('message', check=check)
                    theme = theme_message.content

                    await ctx.send("What date and time is the show? (e.g., 17 Oct at 22)")
                    date_message = await self.bot.wait_for('message', check=check)
                    date_str = date_message.content

                    # Parse and format the date
                    discord_timestamp = parse_date(date_str)

                    if discord_timestamp:
                        show = {"theme": theme, "date": discord_timestamp, 'started': False, 'inProgress': False, "participants": []}
                        coc_info["shows"].append(show)
                        save_json(json_file_path, coc_info)
                        await ctx.send(f"New show created with theme: {theme} Date/Time: {discord_timestamp}")
                    else:
                        await ctx.send("Invalid date format. Please use the format: 17 Oct at 22")

                elif create_new_response == 'no':
                    await ctx.send("No changes made. Current show is preserved.")

                else:
                    await ctx.send("Invalid response. Command cancelled.")
        else: 
            await ctx.send("Sorry mate. You can't run this command.")

    @commands.command(name='coclist', brief="[Admin-Only] List song names, artists and music links")
    async def coc_list(self, ctx):
        if ctx.author.guild_permissions.administrator:
            json_file_path = 'data/cocshow.json'
            coc_info = load_json(json_file_path)

            # Find the upcoming show
            upcoming_show = next((show for show in coc_info["shows"] if not show["started"]), None)

            if upcoming_show:
                # Create an embed to display upcoming COC music
                embed = nextcord.Embed(
                    title="Upcoming COC Music",
                    color=0x3498db  # Bright sky blue color
                )

                # Check if the upcoming show has participants
                if upcoming_show.get("participants"):
                    # Order participants by points
                    ordered_participants = sorted(upcoming_show["participants"], key=lambda p: p.get('points', 0), reverse=True)

                    # Add fields for each participant's music
                    for i, participant in enumerate(ordered_participants, start=1):
                        name = participant.get('name', '')
                        song_name = participant.get('song_name', '')
                        artist_name = participant.get('artist_name', '')
                        youtube_link = participant.get('youtube_link', '')

                        # Add a field for the current participant's music
                        embed.add_field(name=f"#{i} - ({name}) {song_name} by {artist_name}", value=f"[Listen]({youtube_link})", inline=False)

                # Send the embed
                await ctx.send(embed=embed)
            else:
                await ctx.send("No upcoming shows found.")

    @commands.command(name='cocstart', brief="[Admin-Only] Shuffle and start tournament")
    async def coc_start(self, ctx):   
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        if ctx.author.guild_permissions.administrator:
            # Find the next show that hasn't started and isn't in progress
            next_show = next((show for show in coc_info["shows"] if not show.get("started", False) and not show.get("inProgress", False)), None)

            if next_show:
                # Mark the show as started
                next_show["started"] = True
                next_show["inProgress"] = True
                save_json(json_file_path, coc_info)

                # Shuffle participants for the initial round
                participants = next_show.get("participants", [])
                shuffled_participants = random.sample(participants, len(participants))

                # Pair up the shuffled participants for the initial round
                initial_round_pairs = list(itertools.zip_longest(shuffled_participants[::2], shuffled_participants[1::2]))

                # Create a new tournament on Challonge
                tournament_name = f"COC Championship - {next_show['theme']}"
                tournament_type = 'single elimination'  # You can change this to 'double elimination' if needed

                challonge_api_key = 'HzmN3tXDeYSAAlqehu8jc2LtYacIiup17tQnsyIY'
                url = f'https://api.challonge.com/v1/tournaments.json'
                data = {
                    'api_key': challonge_api_key,
                    'tournament[name]': tournament_name,
                    'tournament[tournament_type]': tournament_type,
                    'tournament[game_name]': 'Music',
                    'tournament[hold_third_place_match]': 1  # Set this parameter to enable the match for 3rd place
                }
                # Set a custom User-Agent header
                headers = {
                    'User-Agent': 'MyCoolCOCApp/1.0 (Contact: jnunopaivaa@gmail.com)',
                }

                response = requests.post(url, data=data, headers=headers)

                # Check if the request was successful
                if response.status_code == 200:
                    created_tournament = response.json()['tournament']
                    tournament_id = created_tournament['id']
                    tournament_url = created_tournament['full_challonge_url']

                    # Add participants to the Challonge tournament
                    url = f'https://api.challonge.com/v1/tournaments/{tournament_id}/participants/bulk_add.json'
                    data = {
                        'api_key': challonge_api_key,
                        'participants[][name]': [f"{participant['song_name']}" for participant in participants],
                    }

                    # Set a custom User-Agent header
                    headers = {
                        'User-Agent': 'MyCoolCOCApp/1.0 (Contact: jnunopaivaa@gmail.com)',
                    }

                    response = requests.post(url, data=data, headers=headers)

                    # Check if the request was successful
                    if response.status_code == 200:
                        print('Participants added to Challonge tournament successfully!')
                        print(f'Tournament URL: {tournament_url}')
                        await ctx.send(f"⚠️ Concurso Original da Canção **{next_show['theme']}** has started!! :warning:")
                        await ctx.send(f"\nTournament Link:\n{tournament_url}")
                    else:
                        print(f'Error adding participants to Challonge tournament: {response.text}')
                else:
                    print(f'Error creating Challonge tournament: {response.text}')

                # Send an initial message with tournament information
                embed = nextcord.Embed(
                    title=tournament_name,
                    color=0x3498db  # Bright sky blue color
                )
                embed.add_field(name="Stage", value="Initial Matchups:", inline=False)

                # Display the initial matchups in the embed
                for i, matchup in enumerate(initial_round_pairs, start=1):
                    field_value = ""
                    for participant in matchup:
                        if participant:
                            field_value += f"{participant['song_name']} by {participant['artist_name']}\n"
                    embed.add_field(name=f"Matchup #{i}", value=field_value, inline=False)

                embed.add_field(name="Where", value="Watch it live here:\nhttps://www.twitch.tv/nuuunu", inline=True)
                # Your logic to start the show goes here
                await ctx.send(embed=embed)
            else:
                await ctx.send("No upcoming shows to start.")
        else:
            await ctx.send("Sorry mate. You can't run this command.")

    @commands.command(name='cocdownload', brief="[Admin-Only] Downloads songs")
    async def coc_download(self, ctx):  
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        if ctx.author.guild_permissions.administrator:
            # Your existing code...

            next_show = next((show for show in coc_info["shows"] if not show.get("started", False) and not show.get("inProgress", False)), None)

            if next_show:

                # Shuffle participants for the initial round
                participants = next_show.get("participants", [])

                # Create a list of YouTube links from the participants' song URLs
                video_links = [participant.get('youtube_link') for participant in participants]

                # Get the user's home directory
                home_dir = os.path.expanduser("~")

                # Construct the path to the Downloads folder
                downloads_folder = os.path.join(home_dir, 'Downloads')

                # Specify the filename
                filename = 'links.txt'

                # Combine the Downloads folder and filename to create the full path
                links_file_path = os.path.join(downloads_folder, filename)

                # Now, links_file_path contains the path to the 'links.txt' file in the user's Downloads folder
                print(links_file_path)
                # Write the YouTube links to the file
                with open(links_file_path, 'w') as file:
                    file.write('\n'.join(filter(None, video_links)))

                # Specify the folder where you want to save the downloaded videos
                output_folder_path = downloads_folder

                # Download YouTube videos
                download_youtube_videos(links_file_path, output_folder_path)

                await ctx.send(f"Downloaded songs successfully!")
            else:
                await ctx.send("No upcoming shows to start.")
        else:
            await ctx.send("Sorry mate. You can't run this command.")

    @commands.command(name='cocwinners', brief="[Admin-Only] Select winners for the last show")
    async def coc_winners(self, ctx):
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        if ctx.author.guild_permissions.administrator:

            # Find the last started show with participants
            last_show_participants = next((show for show in reversed(coc_info["shows"]) if show["started"] and show.get("inProgress") and show.get("participants")), None)

            if last_show_participants:
                # Extract participants from the last show
                participants = last_show_participants.get("participants", [])

                # Check if any participant already has points
                if any(participant.get('points', 0) != 0 for participant in participants):
                    await ctx.send("Winners for the last show have already been edited! Command cancelled.")
                    return

                # Create an embed with the participants list
                embed = nextcord.Embed(
                    title="Select Winners for the Last Show",
                    color=0x87CEEB  # Bright sky blue color
                )

                participants_str = "\n".join([f"{i + 1}. {participant['name']} (+{participant['points']}pts)\n  Song: {participant['song_name']} by {participant['artist_name']}" for i, participant in enumerate(participants)])
                embed.add_field(name="Participants", value=participants_str, inline=False)

                # Send the embed and ask for winners
                message = await ctx.send(embed=embed)
                await ctx.send("Reply with the winners in the format: `1st, 2nd, 3rd, 4th`")

                # Wait for the user's response
                winners_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

                # Process the winners and update the embed
                await self.process_winners(ctx, message, winners_message.content, participants, json_file_path, coc_info, last_show_participants)

                # Set inProgress to False for the last show
                last_show_participants["inProgress"] = False

                # Save the updated JSON to the file
                save_json(json_file_path, coc_info)

            else:
                await ctx.send("No started shows with participants found.")
        else:
            await ctx.send("Sorry mate. You can't run this command.")

    async def process_winners(self, ctx, message, winners_str, participants, json_file_path, coc_info, last_show_participants):

        # Load or create participant in the stats
        stats_file_path = 'data/cocstats.json'
        stats_info = load_jsonSTATS(stats_file_path)
        stats_participants = stats_info.get("participants", [])

        positions = ['1st', '2nd', '3rd', '4th']

        # Split the user's response to get the winners
        winners = [winner.strip() for winner in winners_str.split(',')]

        # Validate the number of winners
        if len(winners) != len(positions):
            await ctx.send("Invalid number of winners. Command cancelled.")
            return

         # Assign points to winners
        for position, winner_name in zip(positions, winners):
            participant = next((p for p in participants if p['name'] == winner_name), None)
            if participant:
                # Update the participant with points
                points = self.get_points_by_position(position)
                participant['points'] = participant.get('points', 0) + points

        # Create a new embed with the updated information
        new_embed = nextcord.Embed(
            title="Winners of the Last Show",
            color=0x3498db  # Bright sky blue color
        )

        # Order participants by points
        ordered_participants = sorted(participants, key=lambda p: p.get('points', 0), reverse=True)

        # Get the maximum number of participants to determine the positions list length
        max_participants = min(len(ordered_participants), len(positions))

        # Create a new embed with the updated information
        new_embed = nextcord.Embed(
            title="Winners of the Last Show",
            color=0x3498db  # Bright sky blue color
        )

        # Clear existing fields
        new_embed.clear_fields()

        # Update the embed with the winners' points
        for participant in ordered_participants[:max_participants]:
            name = participant['name']
            points = participant.get('points', 0)

            # Update participant data in the JSON for the current show
            if last_show_participants and last_show_participants.get("participants"):
                for p in last_show_participants["participants"]:
                    if p['name'] == name:
                        p['points'] = points
                        break
                
            # Find or create participant in the stats
            stats_participant = next((p for p in stats_participants if p['name'] == name), None)
            if not stats_participant:
                stats_participant = {
                    "name": name,
                    "total_points": 0,
                    "1st_place_count": 0,
                    "2nd_place_count": 0,
                    "3rd_place_count": 0,
                    "4th_place_count": 0
                }
                stats_participants.append(stats_participant)

            # Update stats
            stats_participant['total_points'] += points

            # Determine the position for this participant
            position = positions[ordered_participants.index(participant)]
            stats_participant[f"{position.lower()}_place_count"] += 1


            # Add participant to the embed
            new_embed.add_field(name=f"{name} (+{points}pts)", value=f"Song: {participant['song_name']} by {participant['artist_name']}", inline=False)

        # Save the updated JSON to the file
        save_json(json_file_path, coc_info)
        
        # Save updated stats to the file
        stats_info["participants"] = stats_participants  # Ensure the "participants" key exists
        save_json(stats_file_path, stats_info)

        # Update the message with the modified embed
        await message.edit(embed=new_embed)
        await ctx.send("Done!")

    #================================================
                    #CLIENT COMMANDS
    #================================================

    @commands.command(name='cocjoin', brief="Edit entry/Change song")
    async def coc_join(self, ctx):
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        def check(message):
            return message.author == ctx.author and isinstance(message.channel, nextcord.DMChannel)

        # Find the next show that hasn't started
        next_show = None
        for show in coc_info["shows"]:
            if not show.get("started", False):
                next_show = show
                break

        if next_show:
            # Check if the user has already joined
            user_already_joined = any(participant["name"] == str(ctx.author) for participant in next_show["participants"])

            if user_already_joined:
                await ctx.send("You already joined this show. Do **!cocedit** to change your music.")
            else:
                await ctx.author.send("What's the title of your song?")
                song_name_message = await self.bot.wait_for('message', check=check)
                song_name = song_name_message.content.capitalize()

                await ctx.author.send("And who's the artist?")
                artist_name_message = await self.bot.wait_for('message', check=check)
                artist_name = artist_name_message.content.capitalize()

                await ctx.author.send("Please provide a YouTube link to this song.")
                youtube_link_message = await self.bot.wait_for('message', check=check)
                youtube_link = youtube_link_message.content

                await ctx.author.send("Alright, let me validate this for you. One sec!")

                # Validate the YouTube link and video duration
                with yt_dlp.YoutubeDL() as ydl:
                    try:
                        video_info = ydl.extract_info(youtube_link, download=False)

                        # Check if it's a valid YouTube link
                        if video_info.get('extractor', '') != 'youtube':
                            raise yt_dlp.DownloadError("Invalid YouTube link.")

                        # Check if the video duration is less than 5 minutes
                        if video_info.get('duration', 0) > 300:
                            raise yt_dlp.DownloadError("Video duration exceeds 5 minutes.")

                    except yt_dlp.DownloadError:
                        await ctx.author.send("Invalid YouTube link or video duration exceeds 5 minutes. Please run ``!cocjoin`` to try again!")
                        return

                # Add the user to the participants list
                participant = {"name": str(ctx.author), "song_name": song_name, "artist_name": artist_name, "youtube_link": youtube_link, "points": 0}
                next_show["participants"].append(participant)
                save_json(json_file_path, coc_info)

                await ctx.author.send(f"Successfully joined the COC show with the song: {song_name} by {artist_name}. Good luck, friend!")
        else:
            await ctx.send("No upcoming shows to join.")
   
    @commands.command(name='cocedit', brief="Edit entry/Change song")
    async def coc_edit(self, ctx):
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        def check(message):
            return message.author == ctx.author and isinstance(message.channel, nextcord.DMChannel)

        # Find the next show that hasn't started
        next_show = next((show for show in coc_info["shows"] if not show.get("started", False)), None)

        if next_show:
            # Check if the user has already joined
            user_entry = next((participant for participant in next_show["participants"] if participant["name"] == str(ctx.author)), None)

            if user_entry:
                # Create an embed for editing
                embed = nextcord.Embed(
                    title="Edit Your Entry",
                    description="You can edit your song information below.",
                    color=0x00ff00
                )

                embed.add_field(name="Current Song", value=user_entry["song_name"], inline=True)
                embed.add_field(name="Artist", value=user_entry["artist_name"], inline=True)
                embed.add_field(name="Music Link", value=user_entry["youtube_link"], inline=False)

                await ctx.author.send(embed=embed)
                await ctx.author.send("What's the new name of your song? (Type 'cancel' to cancel)")

                # Wait for the new song name
                new_song_name_message = await self.bot.wait_for('message', check=check)
                new_song_name = new_song_name_message.content

                if new_song_name.lower() != 'cancel':
                    await ctx.author.send("What's the new name of the artist? (Type 'cancel' to cancel)")

                    # Wait for the new artist name
                    new_artist_name_message = await self.bot.wait_for('message', check=check)
                    new_artist_name = new_artist_name_message.content

                    if new_artist_name.lower() != 'cancel':
                        await ctx.author.send("Please provide the new YouTube link to this song. (Type 'cancel' to cancel)")

                        # Wait for the new YouTube link
                        new_youtube_link_message = await self.bot.wait_for('message', check=check)
                        new_youtube_link = new_youtube_link_message.content

                        if new_youtube_link.lower() != 'cancel':
                            # Validate the new YouTube link and video duration
                            with yt_dlp.YoutubeDL() as ydl:
                                try:
                                    video_info = ydl.extract_info(new_youtube_link, download=False)

                                    # Check if it's a valid YouTube link
                                    if video_info.get('extractor', '') != 'youtube':
                                        raise yt_dlp.DownloadError("Invalid YouTube link.")

                                    # Check if the video duration is less than 5 minutes
                                    if video_info.get('duration', 0) > 300:
                                        raise yt_dlp.DownloadError("Video duration exceeds 5 minutes.")

                                    # Update the user's entry
                                    user_entry["song_name"] = new_song_name
                                    user_entry["artist_name"] = new_artist_name
                                    user_entry["youtube_link"] = new_youtube_link

                                    # Update the JSON file
                                    save_json(json_file_path, coc_info)

                                    await ctx.author.send("Your entry has been updated!")
                                except yt_dlp.DownloadError as e:
                                    await ctx.send(str(e))
                                except Exception as e:
                                    await ctx.author.send(f"An error occurred: {str(e)}")
                        else:
                            await ctx.author.send("Edit cancelled. No changes made.")
                    else:
                        await ctx.author.send("Edit cancelled. No changes made.")
                else:
                    await ctx.author.send("Edit cancelled. No changes made.")

            else:
                await ctx.send("You haven't joined the show yet. Use ``!cocjoin`` to join.")
        else:
            await ctx.send("No upcoming shows to edit.")

    @commands.command(name='coc', brief="Embed w/ theme, date & entries!")
    async def coc(self, ctx):
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        # Find the next show that hasn't started
        next_show = next((show for show in coc_info["shows"] if not show.get("started", False)), None)

        if next_show:
            # Create an embed with information about the upcoming show
            embed = nextcord.Embed(
                title="Upcoming COC Information",
                color=0x87CEEB 
            )

            embed.add_field(name="Rules", value="<5min song", inline=False)
            embed.add_field(name="Theme", value=next_show["theme"], inline=True)
            embed.add_field(name="Date", value=next_show["date"], inline=True)

            # Display the number of participants and their names
            participants_str = "\n".join([f"{i + 1}. {participant['name']}" for i, participant in enumerate(next_show["participants"])])
            embed.add_field(name=f"Participants ({len(next_show['participants'])})", value=participants_str, inline=False)
            embed.add_field(name="Where", value="Watch it live here:\nhttps://www.twitch.tv/nuuunu", inline=True)
            
            user_entry = next((participant for participant in next_show["participants"] if participant["name"] == str(ctx.author)), None)
            if not user_entry:
                embed.add_field(name="Join", value="Run ``!cocjoin``to join!", inline=True)

            await ctx.send(embed=embed)
        else:
            await ctx.send("No upcoming shows.")

    @commands.command(name='mycoc', brief="Info about your own entry")
    async def coc_info(self, ctx):
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        # Find the next show that hasn't started
        next_show = next((show for show in coc_info["shows"] if not show.get("started", False)), None)

        if next_show:
            # Check if the user has already joined
            user_entry = next((participant for participant in next_show["participants"] if participant["name"] == str(ctx.author)), None)

            if user_entry:
                # Create an embed for editing
                embed = nextcord.Embed(
                    title="Your Song Details",
                    description="You can view your song information below.",
                    color=0x00ff00
                )

                embed.add_field(name="Current Song", value=user_entry["song_name"], inline=True)
                embed.add_field(name="Artist", value=user_entry["artist_name"], inline=True)
                embed.add_field(name="Music Link", value=user_entry["youtube_link"], inline=False)

                await ctx.author.send(embed=embed)
            else:
                await ctx.send("You haven't joined the current show.")
        else:
            await ctx.send("No upcoming shows.")

    @commands.command(name='cocstats', brief="Show current stats and standings")
    async def coc_stats(self, ctx):
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        # Create a dictionary to store total points and show-wise highest scores for each participant
        total_points = {}
        show_highest_scores = {}

        # Iterate through each show in reverse order
        for show in reversed(coc_info["shows"]):
            participants = show.get("participants", [])

            # Update total points and highest scores for each participant
            for participant in participants:
                name = participant["name"]
                points = participant.get("points", 0)
                total_points[name] = total_points.get(name, 0) + points

                # Update highest score for the participant for the current show
                show_highest_scores[name] = max(show_highest_scores.get(name, 0), points)

        # Order participants by total points
        ordered_participants = sorted(total_points.items(), key=lambda x: x[1], reverse=True)

        # Create an embed with the rankings
        embed = nextcord.Embed(
            title="COC 2.0 Standings",
            color=0xFFD700  # Gold color
        )

        # Add rankings to the embed
        for i, (name, points) in enumerate(ordered_participants, start=1):
            medal = self.get_medal_emoji(i)
            embed.add_field(name=f"{medal} {name}", value=f"Points: {points}", inline=False)

        # Send the embed
        await ctx.send(embed=embed)

    def get_medal_emoji(self, position):
        if position == 1:
            return '🥇'  # Gold medal
        elif position == 2:
            return '🥈'  # Silver medal
        elif position == 3:
            return '🥉'  # Bronze medal
        else:
            return '🍆'  # Fourth place

    @commands.command(name='cochistory', brief="Show #1 & #2 songs of each week")
    async def coc_history(self, ctx):
        json_file_path = 'data/cocshow.json'
        coc_info = load_json(json_file_path)

        # Create an embed to display COC history
        embed = nextcord.Embed(
            title="COC 2.0 Music History",
            color=0x3498db  # Bright sky blue color
        )

        # Iterate through each show in reverse order
        for i, show in enumerate(reversed(coc_info["shows"]), start=1):
            show_name = show.get("theme", f"COC #{i}")
            field_content = ""

            # Check if the show has started, is not finished, and has participants
            if show["started"] and not show.get("finished", False) and show.get("participants"):
                # Order participants by points
                ordered_participants = sorted(show["participants"], key=lambda p: p.get('points', 0), reverse=True)

                # Extract information for 1st and 2nd place
                for position, emoji in zip(['1st', '2nd'], ['🥇', '🥈']):
                    if len(ordered_participants) >= int(position[0]):
                        participant = ordered_participants[int(position[0]) - 1]
                        name = participant['name']
                        points = participant.get('points', 0)
                        song_name = participant.get('song_name', '')
                        artist_name = participant.get('artist_name', '')
                        youtube_link = participant.get('youtube_link', '')

                        # Construct the field content
                        field_content += f"{emoji} {song_name} by {artist_name}: [Listen]({youtube_link})\n"

            # Add a field for the current show
            if field_content:
                embed.add_field(name=show_name, value=field_content, inline=False)

        # Send the embed
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(COC(bot))
