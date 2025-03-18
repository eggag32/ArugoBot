# ArugoBot
When my friends and I were practicing for competitive programming contests we used [Arugo](https://github.com/phattd15/arugo) quite a bit, and it was a lot of fun.
After some time it stopped being hosted (I rehosted it [here](https://eggag33.pythonanywhere.com/) and it seems to work though).
So I decided to write a Discord bot with similar functionality: my hope is that it makes it more convenient and fun to practice with others.
Credit (and thanks!) to [phattd15](https://github.com/phattd15)/[polarity-ac](https://github.com/polarity-ac) for the original idea!

## Usage
The following commands are available to you:

- **=challenge [problem (i.e. 1000A)] [length in minutes (40/60/80)] [participants other than you (i.e. @eggag32 @eggag33)]**

  Starts a challenge.
- **=rating [optional username (i.e. @eggag32)]**
  
  Shows your (or other user's) rating graph.
- **=history [optional username (i.e. @eggag32)] [optional page number, 1 by default]**

  Shows a page of your (or someone else's) challenge history.
- **=leaderboard [optional page number, 1 by default]**

  Shows a page of the server leaderboard.
- **=register [handle]**

  Links your CF account.
- **=unlink**

  Unlinks your CF account and erases all progress.
- **=suggest [rating] [users to suggest for other than you (i.e. @eggag32 @eggag33)]]**

  Gives some problems at a given rating that none of the users have done.
- **=help**

  Prints the help message.

## Installation
To invite the instance I am hosting, use this [link](https://discord.com/oauth2/authorize?client_id=1325529003473240124&permissions=277025507392&integration_type=0&scope=bot).
If you want to host it yourself, you need to make sure you install everything from ```requirements.txt```, add a ```token.txt``` file that contains your Discord bot token, add a ```proxies.json``` file with the proxies (or change ```proxy.py``` to not use them), and run ```main.py```.
