import streamlit as st
import requests
import re
from youtubesearchpython import VideosSearch
import base64
from yt_dlp import YoutubeDL
from io import BytesIO
import datetime

# Spotify API credentials
client_id = '0ee393dc28944766855298a4da69e4d4'
client_secret = 'e86ba0783d444176abb20514cefb3674'


# Function to get Spotify access token
def get_access_token():
    # Make a request to the Spotify API to get an access token
    response = requests.post('https://accounts.spotify.com/api/token',
                             headers={'Authorization': 'Basic ' + base64_encode(client_id + ':' + client_secret)},
                             data={'grant_type': 'client_credentials'})
    response.raise_for_status()
    json_response = response.json()
    access_token = json_response['access_token']
    return access_token


# Function to encode client_id and client_secret for Authorization header
def base64_encode(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')


def download_youtube_audio(url, quality):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': quality,
        }],
        'outtmpl': 'downloaded_audio.%(ext)s',
        'noplaylist': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        info_dict = ydl.extract_info(url, download=False)
        audio_filename = ydl.prepare_filename(info_dict).replace('.webm', '.mp3')
    with open(audio_filename, 'rb') as f:
        audio_bytes = BytesIO(f.read())
    return audio_bytes


def get_music_name(track_id):
    # Get the music name and artist from the Spotify API using the track ID
    access_token = get_access_token()
    response = requests.get(f'https://api.spotify.com/v1/tracks/{track_id}',
                            headers={'Authorization': 'Bearer ' + access_token})
    response.raise_for_status()
    json_response = response.json()
    # Extract the music name and artist from the API response
    music_name = json_response['name']
    artist = json_response['artists'][0]['name']
    # Concatenate the music name and artist for the YouTube search query
    search_query = f"{music_name} {artist}"
    return search_query


def extract_album_id(url):
    match = re.search(r'album\/([\w]+)', url)
    if match:
        return match.group(1)
    else:
        raise ValueError('Invalid Spotify album URL')


def extract_track_ids(url):
    # Extract the track IDs from the Spotify playlist URL or individual Spotify music URL
    if 'playlist' in url:
        playlist_id = extract_playlist_id(url)
        return get_track_ids_from_playlist(playlist_id)
    elif 'track' in url:
        track_id = extract_track_id(url)
        return [track_id]
    elif 'album' in url:
        album_id = extract_album_id(url)
        return get_track_ids_from_album(album_id)
    else:
        raise ValueError("Invalid Spotify URL.")


def get_track_ids_from_album(album_id):
    access_token = get_access_token()
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
    response.raise_for_status()
    json_response = response.json()
    track_ids = [track["id"] for track in json_response["items"]]
    return track_ids


def extract_playlist_id(url):
    # Extract the playlist ID from the Spotify playlist URL
    match = re.search(r'playlist\/([\w]+)', url)
    if match:
        playlist_id = match.group(1)
        return playlist_id
    else:
        raise ValueError("Invalid Spotify playlist URL.")


def extract_track_id(url):
    # Extract the track ID from the individual Spotify music URL
    match = re.search(r'track\/([\w]+)', url)
    if match:
        track_id = match.group(1)
        return track_id
    else:
        raise ValueError("Invalid Spotify music URL.")


def get_track_ids_from_playlist(playlist_id):
    access_token = get_access_token()
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
    response.raise_for_status()
    json_response = response.json()
    track_ids = [item["track"]["id"] for item in json_response["items"]]
    return track_ids


def search_on_youtube(query):
    # Search for the given query on YouTube using youtube-search-python
    videos_search = VideosSearch(query, limit=1)
    results = videos_search.result()
    if results['result']:
        # Extract the YouTube URL of the first search result
        youtube_url = results['result'][0]['link']
        return youtube_url
    return None


def add_bg_from_local(image_file):
    with open(image_file, "rb") as file:
        encoded_string = base64.b64encode(file.read())

    st.markdown(
        f"""
        <style>
          .stApp {{
              background-image: url(data:image/png;base64,{encoded_string.decode()});
              background-size: cover;
              text-align: center;
          }}
          div.stTextInput input {{
              text-align: center;
          }}
          div.stTextInput div.stTextInputClearer {{
              margin-left: auto;
              margin-right: auto;
              display: block;
              text-align: center;
          }}
        </style>
        """,
        unsafe_allow_html=True
    )


def main():
    st.set_page_config(page_title="Music Mate", page_icon="🎵")
    add_bg_from_local('background.jpg')

    st.title('Music Mate')

    with st.sidebar:
        st.header("Audio Quality")
        quality = st.radio(
            "Choose the quality of the audio:",
            ('128', '192', '256')
        )

    url = st.text_input('Enter Spotify or YouTube URL', key='url')

    if st.button('Download'):
        try:
            if 'youtube.com' in url or 'youtu.be' in url:
                # download youtube song
                audio_stream_bytes = download_youtube_audio(url, quality)
                st.audio(audio_stream_bytes, format='audio/mp3')
                st.success('Download complete!')
            elif 'spotify.com' in url:
                track_ids = extract_track_ids(url)
                if not track_ids:
                    st.error("No tracks found in playlist")
                for track_id in track_ids:
                    music_name = get_music_name(track_id)
                    youtube_url = search_on_youtube(music_name)
                    if youtube_url:
                        audio_stream_bytes = download_youtube_audio(youtube_url, quality)
                        st.audio(audio_stream_bytes, format='audio/mp3')
                        st.success(f'Download complete for {music_name}!')
                    else:
                        st.warning(f"No matching video found for {track_id}")
                st.info("Done downloading all songs")
            else:
                st.error("Invalid URL")
        except Exception as e:
            st.error(str(e))

    st.markdown(
        """
        <br><br>
        Follow me on:
        <br>
        [![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/SamirSengupta)
        [![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/samirsengupta/)
        """,
        unsafe_allow_html=True
    )


if __name__ == '__main__':
    main()
