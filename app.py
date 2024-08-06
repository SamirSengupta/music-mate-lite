import streamlit as st
import requests
import re
from youtubesearchpython import VideosSearch
import base64
from yt_dlp import YoutubeDL
from io import BytesIO
import json
import os

# File to store user data
USER_DATA_FILE = 'sec.json'

# Spotify API credentials
client_id = '0ee393dc28944766855298a4da69e4d4'
client_secret = 'e86ba0783d444176abb20514cefb3674'

# Function to get Spotify access token
def get_access_token():
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

# Progress hook function to track download progress
def progress_hook(d):
    if d['status'] == 'finished':
        print(f"Done processing {d['filename']}")

def get_youtube_audio_url(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'progress_hooks': [progress_hook]
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            audio_url = info_dict.get('url', None)
            if not audio_url:
                raise ValueError("Failed to get the audio URL.")
            return audio_url

    except Exception as e:
        print(f"Error during processing: {e}")
        raise

def get_music_name(track_id):
    access_token = get_access_token()
    response = requests.get(f'https://api.spotify.com/v1/tracks/{track_id}',
                            headers={'Authorization': 'Bearer ' + access_token})
    response.raise_for_status()
    json_response = response.json()
    music_name = json_response['name']
    artist = json_response['artists'][0]['name']
    search_query = f"{music_name} {artist}"
    return search_query

def extract_album_id(url):
    match = re.search(r'album\/([\w]+)', url)
    if match:
        return match.group(1)
    else:
        raise ValueError('Invalid Spotify album URL')

def extract_track_ids(url):
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
    match = re.search(r'playlist\/([\w]+)', url)
    if match:
        playlist_id = match.group(1)
        return playlist_id
    else:
        raise ValueError("Invalid Spotify playlist URL.")

def extract_track_id(url):
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
    videos_search = VideosSearch(query, limit=1)
    results = videos_search.result()
    if results['result']:
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

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {"users": []}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f)

def login(username, password):
    user_data = load_user_data()
    for user in user_data["users"]:
        if user["username"] == username and user["password"] == password:
            return True
    return False

def signup(username, password):
    user_data = load_user_data()
    for user in user_data["users"]:
        if user["username"] == username:
            return False
    user_data["users"].append({"username": username, "password": password})
    save_user_data(user_data)
    return True

def show_login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(username, password):
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid username or password.")

def show_signup_page():
    st.title("Sign Up")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Sign Up"):
        if signup(username, password):
            st.success("Signup successful! You can now log in.")
        else:
            st.error("Username already exists.")

def main():
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.sidebar.title("Authentication")
        option = st.sidebar.radio("Choose an option", ("Sign Up", "Login"))
        if option == "Login":
            show_login_page()
        elif option == "Sign Up":
            show_signup_page()
        return

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
                audio_url = get_youtube_audio_url(url)
                st.audio(audio_url, format='audio/mp4')
                # st.success('Streaming started!')
            elif 'spotify.com' in url:
                track_ids = extract_track_ids(url)
                if not track_ids:
                    st.error("No tracks found in playlist")
                for track_id in track_ids:
                    music_name = get_music_name(track_id)
                    youtube_url = search_on_youtube(music_name)
                    if youtube_url:
                        audio_url = get_youtube_audio_url(youtube_url)
                        st.audio(audio_url, format='audio/mp4')
                        st.success(f'Streaming started for {music_name}!')
                    else:
                        st.warning(f"No matching video found for {track_id}")
                st.info("Done processing all songs")
            else:
                st.error("Invalid URL")
        except Exception as e:
            st.error(str(e))

    # st.markdown(
    #     """
    #     <br><br>
    #     Follow me on:
    #     <br>
    #     [![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/SamirSengupta)
    #     [![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/samirsengupta/)
    #     """,
    #     unsafe_allow_html=True
    # )

if __name__ == '__main__':
    main()
