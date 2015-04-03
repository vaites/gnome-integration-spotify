Gnome Integration for Spotify
=============================

Provides a better integration in Gnome for Spotify official client on Linux

Features
--------

* Provides commands for multimedia keys
* Shows notifications like Rhythmbox/Banshee with libnotify
* Shows album covers and full song info
* Ability to skip the song directly from the notification
* Manages Spotify URIs (spotify:track:######) 

Requirements
------------

* Mandatory: python-dbus
* Recommended: imagemagick
* Optional: wmctrl, x11-utils, xautomation, xdotool 

Usage
-----

Basic control (*play*, *pause*, *stop*, *prev* or *next*):

    ./spotify-dbus.py ACTION

Daemon mode to shown notifications on song changes:

    ./spotify-dbus.py daemon

Open playlist (Spotify URIs):
    
    -/spotify-dbus.py uri URI

You can also map your multimedia keys with [XBindKeys](http://www.nongnu.org/xbindkeys/xbindkeys.html) and call this script to control Spotify. 

Browsers
========

To allow Firefox/Chrome open playlists:

    gconftool-2 -t string -s /desktop/gnome/url-handlers/spotify/command "/path/to/this/script"
    gconftool-2 -t bool -s /desktop/gnome/url-handlers/spotify/needs_terminal false
    gconftool-2 -t bool -s /desktop/gnome/url-handlers/spotify/enabled true
