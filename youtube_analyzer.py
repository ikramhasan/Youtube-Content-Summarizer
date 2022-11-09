import streamlit as st
import pandas as pd
from pytube import YouTube
import os
import requests
from time import sleep

st.set_page_config(
    page_title="Youtube content summarizer 📝",
    page_icon="🧊",
)

upload_endpoint = "https://api.assemblyai.com/v2/upload"
transcript_endpoint = "https://api.assemblyai.com/v2/transcript"

headers = {
    "authorization": st.secrets["auth_key"],
    "content-type": "application/json"
}

@st.experimental_memo
def save_audio(url):
    yt = YouTube(url)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download()
    base, ext = os.path.splitext(out_file)
    file_name = base + '.mp3'
    os.rename(out_file, file_name)
    print(yt.title + " has been successfully downloaded.")
    print(file_name)
    return yt.title, file_name, yt.thumbnail_url


@st.experimental_memo
def upload_to_AssemblyAI(save_location):
    CHUNK_SIZE = 5242880
    print(save_location)

    def read_file(filename):
        with open(filename, 'rb') as _file:
            while True:
                print("chunk uploaded")
                data = _file.read(CHUNK_SIZE)
                if not data:
                    break
                yield data

    upload_response = requests.post(
        upload_endpoint,
        headers=headers, data=read_file(save_location)
    )
    print(upload_response.json())

    audio_url = upload_response.json()['upload_url']
    print('Uploaded to', audio_url)

    return audio_url


@st.experimental_memo
def start_analysis(audio_url):
    print(audio_url)

    ## Start transcription job of audio file
    data = {
        'audio_url': audio_url,
        'iab_categories': True,
        'content_safety': True,
        "summarization": True,
        "summary_type": "bullets"
    }

    transcript_response = requests.post(transcript_endpoint, json=data, headers=headers)
    print(transcript_response)

    transcript_id = transcript_response.json()['id']
    polling_endpoint = transcript_endpoint + "/" + transcript_id

    print("Transcribing at", polling_endpoint)
    return polling_endpoint


@st.experimental_memo
def get_analysis_results(polling_endpoint):

    status = 'submitted'

    while True:
        print(status)
        polling_response = requests.get(polling_endpoint, headers=headers)
        status = polling_response.json()['status']
        # st.write(polling_response.json())
        # st.write(status)

        if status == 'submitted' or status == 'processing' or status == 'queued':
            print('not ready yet')
            sleep(10)

        elif status == 'completed':
            print('creating transcript')
            st.balloons()
            return polling_response

            break
        else:
            print('error')
            return False
            break

    


st.title("Youtube content summarizer 📝")
st.markdown("With this app you can get a thorough summary of a youtube video and save your precious time 🕐")
st.markdown("You'll get:")
st.markdown("1. A summary of the video")
st.markdown("2. The topics that are discussed in the video")
st.markdown("3. Whether there are any sensitive topics discussed in the video")
st.warning("Just make sure your links are in the format: https://www.youtube.com/watch?v=IDj1OBG5Tpw and not https://youtu.be/IDj1OBG5Tpw")
video_url = st.text_input('Enter Youtube Video Url')
st.markdown('---')

if video_url is not None and video_url.startswith('https://www.youtube.com/watch?v='): 
    video_title, save_location, video_thumbnail = save_audio(video_url)
    st.image(video_thumbnail)
    st.header(video_title)
    st.audio(save_location)

    # Upload mp3 file to assembly ai
    audio_url = upload_to_AssemblyAI(save_location)

    # Start analysis
    polling_endpoint = start_analysis(audio_url)

    # Receive the results
    results = get_analysis_results(polling_endpoint)
    print(results)
    summary = results.json()['summary']
    topics = results.json()['iab_categories_result']['summary']
    sensitive_topics =  results.json()['content_safety_labels']['summary']

    st.markdown('---')
    st.header('Summary of this video')
    st.info(summary)

    st.markdown('---')
    st.header("Sensitive content")
    if sensitive_topics != {}:
        st.markdown('**🚨 Mention of the following sensitive topics detected.**')
        moderation_df = pd.DataFrame(sensitive_topics.items())
        moderation_df.columns = ['topic','confidence']
        st.dataframe(moderation_df, use_container_width=True)
    else:
        st.markdown('**✅ All clear! No sensitive content detected.**') 

    st.markdown('---')
    st.header("Topics discussed in the video")
    topic_lists = list(topics.items())
    st.markdown('1. ' + '  -  '.join(topic_lists[0][0].split('>')))
    st.markdown('2. ' + '  -  '.join(topic_lists[1][0].split('>')))
    st.markdown('3. '+ '  -  '.join(topic_lists[2][0].split('>')))
    # topics_df = pd.DataFrame(topics.items())
    # topics_df.columns = ['topic','confidence']
    # topics_df["topic"] = topics_df["topic"].str.split(">")
    # expanded_topics = topics_df.topic.apply(pd.Series).add_prefix('topic_level_')
    # topics_df = topics_df.join(expanded_topics).drop('topic', axis=1).sort_values(['confidence'], ascending=False).fillna('')
    
    # st.dataframe(topics_df)


