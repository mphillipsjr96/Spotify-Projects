# -*- coding: utf-8 -*-
"""
Created on Sat Feb 13 19:30:18 2021

@author: micha
"""

import requests
import math
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyOAuth
import googlemaps
from datetime import datetime
from ortools.algorithms import pywrapknapsack_solver
import numpy as np

CLIENT_ID = ''#CLIENT ID
CLIENT_SECRET = ''#CLIENT SECRET
CLIENT_REDIRECT_URI = 'http://localhost'
SCOPE = 'user-top-read user-modify-playback-state playlist-modify-private user-read-private'
AUTH_URL = 'https://accounts.spotify.com/api/token'

auth_response = requests.post(AUTH_URL, {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
})

auth_response_data = auth_response.json()

access_token = auth_response_data['access_token']



token = util.prompt_for_user_token(SCOPE,client_id=CLIENT_ID,client_secret=CLIENT_SECRET,redirect_uri=CLIENT_REDIRECT_URI)

sp = spotipy.Spotify(auth=token)
user = sp.me()
USERNAME=user['id']
token = util.prompt_for_user_token(USERNAME,SCOPE,client_id=CLIENT_ID,client_secret=CLIENT_SECRET,redirect_uri=CLIENT_REDIRECT_URI)
sp = spotipy.Spotify(auth=token)

userData = sp.current_user_top_artists(limit=20)

artistIds = []
artistNames = []
artistNamesFull = []
nameidmap = {}
for item in userData['items']:
    artistIds.append(item['id'])
    nameidmap[item['id']]=item['name']
    artistNames.append(item['name'])

client_credentials_manager = SpotifyOAuth(client_id=CLIENT_ID,client_secret=CLIENT_SECRET,redirect_uri=CLIENT_REDIRECT_URI, scope=SCOPE, username=USERNAME)#SpotifyClientCredentials(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

albumData = {}
albumLengths = []
albumNames = []

print("Here are your top artists: ")
for artist in artistNames:
    print(artist)

answer = input("Would you like to remove any? (Y or N): ")
if answer == 'Y':
    removedArtists = input("Who? (Separate by ','): ").split(',')
    for i in range(len(removedArtists)):
        removedArtists[i]=removedArtists[i].strip()
        removedIndex = artistNames.index(removedArtists[i])
        artistIds.pop(removedIndex)
        artistNames.pop(removedIndex)
    
startLoc = input("Where are you? ")
endLoc = input("Where are you headed? ")
gmaps = googlemaps.Client(key='AIzaSyDOF5opG8olbWst4Ui6_Vl35fXHXqJpwbQ')
tripLengthStr = gmaps.directions(startLoc, endLoc, mode="driving", departure_time=datetime.now())[0]['legs'][0]['duration']['text'].split(" ")

if (len(tripLengthStr) == 4) & (tripLengthStr[1]=='day'):
    tripLength = int(tripLengthStr[0])*24*60 + int(tripLengthStr[2])*60
elif len(tripLengthStr) == 4:
    tripLength = int(tripLengthStr[0])*60 + int(tripLengthStr[2])
else:
    tripLength = int(tripLengthStr[0])

albumIdsFull = []
for i,artist in enumerate(artistIds):
    artistAlbums = sp.artist_albums(artist,album_type='album',country='US',limit=50)['items']
    albumIds = []
    for album in artistAlbums:
        if album["name"] not in albumNames:
            albumNames.append(album["name"])
            albumIds.append(album['id'])
            albumIdsFull.append(album['id'])
    for i in range(math.ceil(len(albumIds)/20)):
        if i == 0:
            if len(albumIds) < 20:
                albumIdString = albumIds[:len(albumIds)]
            else:
                albumIdString = albumIds[:20]
        if i == 1:
            if len(albumIds) < 40:
                albumIdString = albumIds[20:len(albumIds)]
            else:
                albumIdString = albumIds[20:40]
        if i == 2:
            albumIdString = albumIds[40:50]
        albums = sp.albums(albumIdString)
        for album in albums['albums']:
            albumLength=0
            for track in album['tracks']['items']:
                albumLength += track['duration_ms']/1000/60
            albumData[album["name"]]=albumLength
            artistNamesFull.append(artistNames[artistIds.index(artist)])  
            albumLengths.append(albumData[album["name"]])
            
#values = albumLengths
values = list(range(0,len(albumLengths)))
np.random.shuffle(values)
weights = [albumLengths]
capacities = [tripLength]

solver = pywrapknapsack_solver.KnapsackSolver(
    pywrapknapsack_solver.KnapsackSolver.
    KNAPSACK_MULTIDIMENSION_BRANCH_AND_BOUND_SOLVER, 'KnapsackExample')

solver.Init(values, weights, capacities)
computed_value = solver.Solve()
packed_ids = []
packed_names = []
packed_weights = []
total_weight = 0
for i in range(len(values)):
    if solver.BestSolutionContains(i):
        packed_ids.append(i)
        packed_names.append(albumNames[i])
        packed_weights.append(weights[0][i])
        total_weight += weights[0][i]

print('\nAlbums:', packed_names)
print('Total Length:', total_weight)
print('Trip Length: ',tripLength)
print('% of Trip: {}%'.format(total_weight/tripLength*100))

answer = input("Create Playlist? (Y/N): ")
idealIds = []
idealTracks = []
if answer == "Y":
    playlist = sp.user_playlist_create(USERNAME, input("Enter playlist name: "), public=False, description='')
    for album in packed_ids:
        aid = albumIdsFull[album]
        idealIds.append(aid)
    if len(idealIds) > 20:
        for i in range(int(len(idealIds)/20)):
            idealAlbumData = sp.albums(idealIds[20*i:20+20*i])
            for album in idealAlbumData['albums']:
                idealTracks = []
                for track in album['tracks']['items']:
                    idealTracks.append(track['uri'])
                sp.user_playlist_add_tracks(USERNAME,playlist['id'],idealTracks)
    else:
        idealAlbumData = sp.albums(idealIds)
        for album in idealAlbumData['albums']:
            idealTracks = []
            for track in album['tracks']['items']:
                idealTracks.append(track['uri'])
            sp.user_playlist_add_tracks(USERNAME,playlist['id'],idealTracks)
    
answer = input("Would you like to start playing? (Y/N): ")
if answer == "Y":
    sp.shuffle(False)
    sp.start_playback(context_uri=playlist['uri'])




