#hello dear colleagues
import gradio as gr
import torch
import platform
import json
from pathlib import Path
from TTS.api import TTS
import uuid
import html
import soundfile as sf

def is_mac_os():
    return platform.system() == 'Darwin'

params = {
    "share": True,
    "activate": True,
    "autoplay": True,
    "show_text": False,
    "remove_trailing_dots": False,
    "voice": "daniel-en.wav",
    "language": "English",
    "model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
}

SAMPLE_RATE = 16000
device = torch.device('cpu') if is_mac_os() else torch.device('cuda:0')

# Load model
tts = TTS(model_name=params["model_name"]).to(device)

# Get available categories (subfolders in targets/)
def get_categories():
    categories_path = Path("targets")
    categories = [folder.name for folder in categories_path.iterdir() if folder.is_dir()]
    return sorted(categories)

# Get speakers for a selected category
def update_speakers(category):
    category_path = Path(f"targets/{category}")
    print("CATPATH"+str(category_path))
    if category_path.exists():
        speakers = [file.stem for file in category_path.glob("*.wav")]
        print(str(speakers))
        return sorted(speakers)
    return []

def update_dropdown_and_audio(category):
    # Fetch the speakers in the selected category
    speakers = update_speakers(category)
    
    # Debug: Print the content of "speakers" for inspection
    print(f"Speakers for category '{category}': {speakers}")
    
    # Return updated dropdown choices, selected value, and reset the audio widget
    return (
        gr.update(choices=speakers, value=speakers[0] if speakers else None),  # Update the dropdown
        speakers[0] if speakers else None,  # Set the selected value
        None  # Reset the audio widget
    )


# Load audio for a specific speaker from a category
def load_speaker_audio(category, speaker_name):
    speaker_path = Path(f"targets/{category}/{speaker_name}.wav")
    if speaker_path.exists():
        return str(speaker_path)
    return None

# Refresh speakers dynamically
def refresh_speakers(category1, category2):
    speakers1 = update_speakers(category1)
    speakers2 = update_speakers(category2)
    return speakers1, speakers2

# Save the recording into the appropriate category
def handle_recorded_audio(audio_data, category, filename):
    if not audio_data or not filename:
        return None, None, None, None

    sample_rate, audio_content = audio_data
    save_path = Path(f"targets/{category}/{filename}.wav")

    # Ensure the directory exists
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the audio file
    sf.write(save_path, audio_content, sample_rate)

    # Refresh speakers automatically after saving
    return refresh_speakers(category, category)

# Generate voice with selected speakers and options
def gen_voice(string, category1, speaker1, category2, speaker2, use_spk1, use_spk2, speed, english):
    string = html.unescape(string)
    short_uuid = str(uuid.uuid4())[:8]
    fl_name = f'outputs/{category1}_{speaker1}_{category2}_{speaker2}_{short_uuid}.wav'
    output_file = Path(fl_name)
    this_dir = str(Path(__file__).parent.resolve())

    speaker_wavs = []
    if use_spk1 and speaker1:
        speaker_wavs.append(f"{this_dir}/targets/{category1}/{speaker1}.wav")
    if use_spk2 and speaker2:
        speaker_wavs.append(f"{this_dir}/targets/{category2}/{speaker2}.wav")

    tts.tts_to_file(
        text=string,
        speed=speed,
        file_path=output_file,
        speaker_wav=speaker_wavs if speaker_wavs else None,
        language=languages[english]
    )
    return output_file

# Load the language data
with open(Path('languages.json'), encoding='utf8') as f:
    languages = json.load(f)

# Gradio Blocks interface
with gr.Blocks() as app:
    gr.Markdown("### TTS based Voice Cloning with Categorized Speakers.")

    with gr.Row():
        with gr.Column():
            text_input = gr.Textbox(
                lines=2,
                label="Speechify this Text",
                value="The quick brown fox jumps over lazy dogs, while bright stars twinkle softly in the night sky."
            )
            speed_slider = gr.Slider(
                label='Speed', minimum=0.1, maximum=1.99, value=0.8, step=0.01)
            language_dropdown = gr.Dropdown(
                list(languages.keys()), label="Language/Accent", value="English")

            gr.Markdown("### Speaker Selection and Voice Cloning")

            with gr.Row():
                with gr.Column():
                    category1_dropdown = gr.Dropdown(choices=get_categories(), label="Category 1", value="neutral")
                    speaker1_dropdown = gr.Dropdown(choices=update_speakers("neutral"), label="Select Speaker 1", value="daniel-en")
                    use_spk1_checkbox = gr.Checkbox(label="Use Speaker 1 in Generation", value=True)
                    speaker1_audio = gr.Audio(value=load_speaker_audio("neutral", "daniel-en"), label="Speaker 1 Audio", interactive=False)
                with gr.Column():
                    category2_dropdown = gr.Dropdown(choices=get_categories(), label="Category 2", value="whispering")
                    speaker2_dropdown = gr.Dropdown(choices=update_speakers("whispering"), label="Select Speaker 2", value="amanda-pt")
                    use_spk2_checkbox = gr.Checkbox(label="Use Speaker 2 in Generation", value=True)
                    speaker2_audio = gr.Audio(value=load_speaker_audio("whispering", "amanda-pt"), label="Speaker 2 Audio", interactive=False)
                refresh_button = gr.Button("Refresh Speakers")

            with gr.Row():
                filename_input = gr.Textbox(
                    label="Save Recording As",
                    placeholder="Enter a name for your recording"
                )
                record_category_dropdown = gr.Dropdown(choices=get_categories(), label="Recording Category", value="neutral")
                record_button = gr.Audio(label="Record Your Voice")
                save_button = gr.Button("Save Recording")

            # Update dropdowns dynamically
            category1_dropdown.change(
              fn=update_dropdown_and_audio,
              inputs=category1_dropdown,
              outputs=[speaker1_dropdown, speaker1_dropdown, speaker1_audio]
            )
            category2_dropdown.change(
             fn=update_dropdown_and_audio,
             inputs=category2_dropdown,
             outputs=[speaker2_dropdown, speaker2_dropdown, speaker2_audio]
            )
            speaker1_dropdown.change(
                fn=lambda spk, cat: load_speaker_audio(cat, spk),
                inputs=[speaker1_dropdown, category1_dropdown],
                outputs=speaker1_audio
            )
            speaker2_dropdown.change(
                fn=lambda spk, cat: load_speaker_audio(cat, spk),
                inputs=[speaker2_dropdown, category2_dropdown],
                outputs=speaker2_audio
            )

            save_button.click(
                fn=handle_recorded_audio,
                inputs=[record_button, record_category_dropdown, filename_input],
                outputs=[
                    speaker1_dropdown,
                    speaker2_dropdown
                ]
            )
            refresh_button.click(
                fn=refresh_speakers,
                inputs=[category1_dropdown, category2_dropdown],
                outputs=[
                    speaker1_dropdown,
                    speaker2_dropdown
                ]
            )

        with gr.Column():
            submit_button = gr.Button("Convert")
            audio_output = gr.Audio()

            submit_button.click(
                fn=gen_voice,
                inputs=[
                    text_input, 
                    category1_dropdown, 
                    speaker1_dropdown, 
                    category2_dropdown, 
                    speaker2_dropdown, 
                    use_spk1_checkbox, 
                    use_spk2_checkbox, 
                    speed_slider, 
                    language_dropdown
                ],
                outputs=audio_output
            )

if __name__ == "__main__":
    app.launch(
        root_path="/tts",
        auth=("tts", "Text2speecH")
    )

