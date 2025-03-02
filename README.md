# ArugoBot
When my friends and I were practicing for competitive programming contests we used [Arugo](https://github.com/phattd15/arugo) quite a bit, and it was a lot of fun.
After some time it stopped being hosted (I rehosted it [here](https://eggag33.pythonanywhere.com/) and it seems to work though).
So I decided to write a Discord bot with similar functionality: my hope is that it makes it more convenient to practice with others.
Credit (and thanks!) to [phattd15](https://github.com/phattd15)/[polarity-ac](https://github.com/polarity-ac) for the original idea!

## Usage
The following commands are available to you:

- **=challenge [problem (i.e. 1000A)] [length in minutes (40/60/80)] [participants other than you (i.e. @eggag32 @eggag33)]**

  Starts a challenge.
- **=rating**
  
  Shows your rating.
- **=register [handle]**

  Links your CF account.
- **=unlink**

  Unlinks your CF account and erases all progress.
- **=suggest [rating] [list of CF handles]**

  Gives some problems at a given rating that none of the CF accounts have done.
- **=help**

  Prints the help message.

## Installation
To invite the instance I am hosting, use this [link](https://discord.com/oauth2/authorize?client_id=1325529003473240124).
If you want to host it, all you need to do is make sure you install everything from ```requirements.txt```, add a ```token.txt``` file that contains your Discord bot token, and run ```main.py```.
