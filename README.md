# A-Moebe

A-Moebe is a gamerunner which is used for an escaperoom made with Python and JavaScript and a whole bunch of Raspberry Pi's.

@kevvie303 is the mastermind behind this gamerunner, having written all the code from scratch. A few examples of the things he made possible are:
* Creating a localhost on the Pi which you can also use on other locations;
* Writing code that allows you to lock and unlock magnets, and also control keypads to unlock a magnet;
* Creating a system with which you can add, control, play, pause, resume and delete media files. Playing is controlled over multiple soundcards and multiple pi's;
* Making sure it's possible to use buttons on the localhost in your browser that can control the magnets;
* Making the basic styling.
  
@romyjkk makes sure the HTML is semantic and the CSS is done the 'right' way.

Both of us are students who are doing this as a side project to learn more about the topics we're interested in and use our skills to help our friend who's dream it is to make his own escaperoom.  

## How to setup github with the raspberry pi:  
Connect to the right pi by using Putty and entering the right IP-address:  
`top-pi`, mostly used for sensors/maglocks: `192.168.0.104`  
`middle-pi`, mostly used for the playing of music: `192.168.0.105`  
`tree-pi`, only used for everything in the tree: `192.168.0.114`  
First update the pi with the following commands:  
`sudo apt-get update`  
`sudo apt-get upgrade` (then entering y)  
`sudo reboot`  
Reconnect to the pi and enter the following commands:  

`git config --global user.email "kvbaar@hotmail.nl"`  
`git config --global user.name "Kevin"`  
`ssh-keygen -t ed25519 -C "kvbaar@hotmail.nl"`  
Then press enter 3 times.  
`eval "$(ssh-agent -s)"`  
`ssh-add ~/.ssh/id_ed25519`  
`cat ~/.ssh/id_ed25519.pub`  
Now you copy everything that it gives as a return, for example: "ssh-ed25519 fiuhewhiufheuifrehriufersugiegierbugsbibisigb kvbaar@hotmail.nl"  
`git remote set-url origin git@github.com:kevvie303/[pi].git`, where [pi] needs to be replaced entirely by the name of the right pi, look above for the names.  

