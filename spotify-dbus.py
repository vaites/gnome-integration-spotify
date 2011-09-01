#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# **** BEGIN LICENSE BLOCK ****
# Version: GPL 3.0
#
# The contents of this file are subject to the GNU General Public License Version
# 3.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.gnu.org/licenses/gpl.txt
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# **** END LICENSE BLOCK ****
#
# Gnome Integration for Spotify by David Martínez <gnomeintegration@davidmartinez.net>
#
# Requirements:
#
#		Mandatory: python-dbus
#		Optional : wmctrl, x11-utils, xautomation, xdotool
#
# To allow Firefox/Chrome open playlists:
#
#		gconftool-2 -t string -s /desktop/gnome/url-handlers/spotify/command "/path/to/this/script"
#		gconftool-2 -t bool -s /desktop/gnome/url-handlers/spotify/needs_terminal false
#		gconftool-2 -t bool -s /desktop/gnome/url-handlers/spotify/enabled true
#
import re
import os
import sys
import dbus
import time
import gobject
import hashlib
import commands
from dbus import Interface
from dbus.mainloop.glib import DBusGMainLoop

# Global variables
pid = False
size = '48x48'
debug = True
cache = os.environ['HOME'] + '/.cache/spotify/Covers/'
timeout = 5000

# Notifier
def show_playing(track = False, interactive = True):
	global nid
	global nloop

	# Debug info
	if debug == True and interactive == True:
		print "Show track data interactively..."
	elif debug == True:
		print "Show track data..."

	# Define actions in notification
	if interactive == True:
		actions = [ '2', 'Siguiente' ]
	else:
		actions = []

	# If track not specified in parameter, read from D-Bus
	if not track:
		track = get_metadata()

	# If there's a song playing
	if track:
		# Get Spotify tray icon coordinates
		coords = get_tray_coords()

		# Configure notification hints
		if coords['x'] > 0:
			hints = { 'x': coords['x'], 'y': coords['y'] }
		else:
			hints = {}

		# Generate notification content
		text = 'por <i>' + get_info(track, 'artist') + '</i> del disco <i>' + get_info(track, 'album') + '</i>'
		text = text.replace('&', '&amp;')

		# Get interface for call notification daemon
		proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		interface = Interface(proxy, dbus_interface='org.freedesktop.Notifications')

		# Closes active notification
		if nid != False:
			if debug == True:
				print "Closing existing notification..."
			
			interface.CloseNotification(nid)

		# Shows notification
		nid = interface.Notify('Spotify', 0, get_cover(), get_info(track, 'title'), text, actions, hints, timeout)

		# Connects to actions signals
		if nid > 0:
			if interactive == True:
				interface.connect_to_signal('ActionInvoked', action_listener)

			interface.connect_to_signal('NotificationClosed', action_dismisser)
			gobject.threads_init()
			gobject.timeout_add(timeout * 10, action_listener)

	return nid

# Paused notifier
def show_paused():
	global nid

	# Debug info
	if debug == True:
		print "Show paused..."

	# Get Spotify tray icon coordinates
	coords = get_tray_coords()

	# Configure notification hints
	if coords['x'] > 0:
		hints = { 'x': coords['x'], 'y': coords['y'] }
	else:
		hints = {}

	# Generate notification content
	text = 'Reproducción pausada'

	# Get interface for call notification daemon
	proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
	interface = Interface(proxy, dbus_interface='org.freedesktop.Notifications')

	# Closes active notification
	if nid != False:
		if debug == True:
			print "Closing existing notification..."
		
		interface.CloseNotification(nid)

	# Shows notification
	nid = interface.Notify('Spotify', 0, '/usr/share/pixmaps/spotify.png', 'Spotify', text, [], hints, timeout)

# Execute an action
def action_trigger(action, param = False):
	if debug == True:
		print "Action '" + action + "' invoked..."

	if action == 'info':
		show_playing()

	elif action == 'next':
		player.Next()

	elif action == 'prev':
		player.Previous()

	elif action == 'play' or action == 'pause':
		if not get_metadata():
			player.Play()
		else:
			player.Pause()

	elif action == 'stop':
		if get_metadata():
			player.Pause()

	elif action == 'quit':
		player.Quit()

	elif action == 'uri':
		if debug == True:
			print "Opening " + param + "..."

		window = get_window()
		window.openLink(param)

# Action listener
def action_listener(id = 0, action = ''):
	global nid

	if id > 0 and id == nid:
		if debug == True and action == 'default':
			print "Notification closed by user..."
		elif debug == True:
			print "Listener received action '" + action + "', invoking action..."

		if action == '0':
			action_trigger('stop')
		elif action == '1':
			action_trigger('play')
		elif action == '2':
			action_trigger('next')
		elif action == '3':
			action_trigger('prev')
			time.sleep(1)
			action_trigger('prev')

		nid = False

# Action dismissed, quits loop
def action_dismisser(id = 0, reason = ''):
	global nid

	if id > 0 and id == nid:
		if debug == True:
			if reason == 1:
				print "Notification expired..."
			elif reason == 2:
				print "Notification dismissed..."
			elif reason == 3:
				print "Notification closed..."
			else:
				print "Notification closed unexpectedly..."

		nid = False

# Track change
def change_listener():
	global playing

	# Gets current song data
	track = get_metadata()

	# Check if Spotify is running
	if pid and not track:
		if int(commands.getoutput("ps ax | awk '{print $1}' | grep -c " + str(pid))) == 0:
			if debug == True:
				print "Spotify not running, exiting..."

			sys.exit()

	# Start playing
	if not playing and track:
		show_playing()
		if debug == True:
			print "Start playing..."

	# Track info changed
	elif playing and track != playing:
		# Paused
		if not track:
			# show_paused()
			if debug == True:
				print "Track paused..."
		
		# Changed
		else:
			show_playing()
			if debug == True:
				info = get_info(track, 'artist') + ' - ' + get_info(track, 'title')
				print "Track changed to " + info + ", show info..."

	# Saves current playing song
	playing = track;

	# Returns true to continue with loop
	return True

# Get formatted info
def get_info(track, item):
	mapped = 'xesam:' + item;
	if item == 'artist':
		for item in track[mapped]:
			info = item
			break
	else:
		info = track[mapped]

	return info.encode('utf-8', 'ignore')

# Get the player object
def get_player():
	try:
		proxyobj = bus.get_object('org.mpris.MediaPlayer2.spotify', '/')
		pl = dbus.Interface(proxyobj, 'org.freedesktop.MediaPlayer2')
	except dbus.DBusException:
		pl = False

	return pl

# Get the window object
def get_window(interface = 'local.sp.SpotifyApplicationLinux'):
	try:
		proxyobj = bus.get_object('org.mpris.MediaPlayer2.spotify', '/MainWindow')
		pl = dbus.Interface(proxyobj, interface)
	except dbus.DBusException:
		pl = False

	return pl

# Get the current track info
def get_metadata():
	try:
		if player != False:
			track = player.GetMetadata()
		else:
			track = False
	except dbus.DBusException:
		track = False

	return track

# Get in-screen coords of tray Spotify icon
def get_tray_coords():
	wmctrl = which('wmctrl')
	xwininfo = which('xwininfo')
	tray_coords = { 'x': 0, 'y': 0 }
	
	if wmctrl != False and xwininfo != False:
		tray = commands.getoutput(wmctrl + ' -l -p | grep "lateral superior" | awk \'{print $1}\'')
		sptfp = commands.getoutput(xwininfo + ' -id ' + tray + ' -tree | grep "spotify" | awk \'{print $6}\'')
		sptfx = commands.getoutput('echo ' + sptfp + ' | awk -F "+" \'{print $2+=10}\'')
		sptfy = commands.getoutput('echo ' + sptfp + ' | awk -F "+" \'{print $3+=13}\'')
		
		tray_coords = { 'x': int(sptfx), 'y': int(sptfy) }

	return tray_coords

# Get current mouse coords
def get_mouse_coords():
	xdotool = which('xdotool')
	mouse_coords = { 'x': 0, 'y': 0 }
	
	if xdotool != False:
		mousex = commands.getoutput("xdotool getmouselocation | awk '{print $1}' | sed -e 's/^x://'")
		mousey = commands.getoutput("xdotool getmouselocation | awk '{print $2}' | sed -e 's/^y://'")
		
		mouse_coords = { 'x': int(mousex), 'y': int(mousey) }

	return mouse_coords

# Gets the album cover based on a track
def get_cover():
	# Gets track info
	track = get_metadata()

	# Check if cache path exists to create it
	global cache
	if not os.path.exists(cache):
		os.system('mkdir "' + cache + '"')
		if debug == True:
			print "Created cache folder..."
	elif debug == True:
		print "Cache folder already exists..."

	# Generate title-based hash to store album cover
	# base = get_info(track, 'artist') + ' - ' + get_info(track, 'album') + ' (' + str(track['year']) + ')'
	base = get_info(track, 'artist') + ' - ' + get_info(track, 'album')
	if debug == True:
		print 'Generating album hash for "' + base + '"'

	h = hashlib.new('md5')
	h.update(base + size)
	hash = h.hexdigest()

	# Check if cover is already downloaded
	path = cache + hash
	if not os.path.exists(path):
		# Generate cover URL
		id = track['xesam:url'].split(':')
		url = 'http://open.spotify.com/track/' + id[2]
		output = commands.getoutput('curl -v ' + url + '| grep \'id="cover-art"\'')
		match = re.search('http(.+)image\/(\w+)', output)

		# Download the cover
		if debug == True:
			print "Downloading cover " + url + "..."

		os.system('wget -q -O ' + path + ' ' + match.group(0))
		os.system('convert -quiet -resize ' + size + ' ' + path + ' ' + path)

		# If download fails uses default Spotify icon
		if not os.path.exists(path):
			path = '/usr/share/pixmaps/spotify.png'
			if debug == True:
				print "Download cover failed..."
		elif debug == True:
			print "Download cover success..."

	elif debug == True:
		print "Cover is already downloaded..."

	return path

# Shows Spotify window
def show_window():
	os.system('touch /tmp/spotify-window.toggle')

	if player.CanRaise():
		if debug == True:
			print "Showing Spotify window..."

		player.Raise()
	elif debug == True:
		print "Cound't show Spotify window..."

# Hides Spotify window
def hide_window():
	os.system('rm -f /tmp/spotify-window.toggle')

	#window = get_window('com.trolltech.Qt.QApplication')
	#window.closeAllWindows()

	#if debug == True:
	#	print "Hiding Spotify window..."

	xte = which('xte')
	tray = get_tray_coords()
	mouse = get_mouse_coords()

	if xte != False and tray['x'] > 0 and mouse['x'] > 0:
		if debug == True:
			print "Hiding Spotify window..."

		commands.getoutput(xte + ' "mousemove ' + str(tray['x']) + ' ' + str(tray['y']) + '" "mousedown 3" "mouseup 3" && sleep 0.01')
		commands.getoutput(xte + ' "mousemove ' + str(tray['x'] + 50) + ' ' + str(tray['y'] + 60) + '" "mousedown 1" "mouseup 1"')
		commands.getoutput(xte + ' "mousemove ' + str(mouse['x']) + ' ' + str(mouse['y']) + '"')
	elif debug == True:
		print "Cound't hide Spotify window..."
		
# Detects if a command exists
def which(cmd):
	path = False
	
	if os.path.exists("/usr/bin/" + cmd): path = "/usr/bin/" + cmd
	elif os.path.exists("/usr/local/bin/" + cmd): path = "/usr/local/bin/" + cmd
	
	return path

# Just launch Spotify in background
def launch():
	spotify = which('spotify')
		
	if spotify != False:
		os.system(spotify + ' > /dev/null 2>&1 &')
		time.sleep(1);
		
		return commands.getoutput('pidof ' + spotify).strip()
	else:
		print 'Spotify cannot be found'
		sys.exit()

# loop must be global to can quit from listener
loop = gobject.MainLoop()

# Prepare loop for interactive notifications or daemon mode
dloop = DBusGMainLoop()
bus = dbus.SessionBus(mainloop=dloop)

# Container of active notification
nid = False

# Container of current playing song
playing = False

# These are defined incorrectly in dbus.dbus_bindings
DBUS_START_REPLY_SUCCESS = 1
DBUS_START_REPLY_ALREADY_RUNNING = 2

# Get the current session bus
bus = dbus.SessionBus()

# Get player object
player = get_player()

# Get notification object
proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
interface = Interface(proxy, dbus_interface='org.freedesktop.Notifications')

# Daemon to listen track change
if 'daemon' in sys.argv or len(sys.argv) == 1:
	# Launch Spotify and wait for it
	if player == False:
		if debug == True:
			print 'Launching Spotify...'

		pid = launch()
		
		time.sleep(3)
		player = get_player()

	os.system('touch /tmp/spotify-window.toggle')

	if debug == True:
		print 'Launching daemon...'

	# Start loop listening for track changes
	try:
		#proxy = bus.get_object('org.mpris.MediaPlayer2.spotify', '/')
		#interface = Interface(proxy, dbus_interface='org.mpris.MediaPlayer2.Player')
		#interface.connect_to_signal('Seeked', change_listener)
		#gobject.threads_init()

		gobject.timeout_add(100, change_listener)
		loop.run()
	except KeyboardInterrupt:
		print 'Stopping daemon...'

# Info
elif 'info' in sys.argv:
	action_trigger('info')

# Next song
elif 'next' in sys.argv:
	action_trigger('next')

# Previous song
elif 'prev' in sys.argv:
	action_trigger('prev')

# Play/pause
elif 'play' in sys.argv or 'pause' in sys.argv:
	action_trigger('play')

# Stop
elif 'stop' in sys.argv:
	action_trigger('stop')

# Quit
elif 'quit' in sys.argv:
	action_trigger('quit')

# Open URI
elif sys.argv[1][0:8] == 'spotify:':
	action_trigger('uri', sys.argv[1])

# Show window
elif 'show' in sys.argv:
	show_window()

# Hide window
elif 'hide' in sys.argv:
	hide_window()

# Toggle window
elif 'toggle' in sys.argv:
	if not os.path.exists('/tmp/spotify-window.toggle'):
		show_window()

	else:
		hide_window()

# Other parameters, error
else:
	if debug == True:
		print "Unknown " + sys.argv[1] + " command..."
