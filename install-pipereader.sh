#!/bin/bash
#set up the pipe that reads command to happen on the clock
#we use a pipe so CGI scripts can easily send commands, and they are
#serialized

sudo rm /usr/local/bin/pipereader.sh
#ahh, that symlink relative path killed me! https://unix.stackexchange.com/a/84178/64038 
sudo ln -s "$(realpath pipereader.sh)" /usr/local/bin/pipereader.sh
sudo cp pipereader.service /etc/systemd/system
sudo systemctl enable pipereader.service
sudo systemctl start pipereader.service
