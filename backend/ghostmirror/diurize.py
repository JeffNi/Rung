import whisperx
from pyannote.audio import Pipeline
import os
from dotenv import load_dotenv
from identify import (
    load_all_embeddings,
    save_new_speaker,
    match_speaker,
    generate_new_speaker_label,
)

EMBEDDING_DIR = "./embeddings"

load_dotenv()
HF_TOKEN = os.environ.get("HF_TOKEN")

def save_transcript(segments, output_path="transcript/interview.txt"):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as f:
        for segment in segments:
            start = segment["start"]
            end = segment["end"]
            speaker = segment["speaker"]
            text = segment["text"]
            f.write(f"[{start:.1f}s - {end:.1f}s] {speaker}: {text}\n")

def transcribe_and_diarize(audio_path, hf_token, device="cpu"):
    speaker_memory = load_all_embeddings()
    existing_labels = {entry["label"] for entry in speaker_memory}

    # Load WhisperX ASR model
    model = whisperx.load_model("base", device=device, compute_type="float32")
    result = model.transcribe(audio_path, language="en")

    # Diarization
    diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization@2.1",
        use_auth_token=hf_token
    )
    diarization_result = diarization_pipeline(audio_path)

    speaker_labels = {}
    for segment in diarization_result["segments"]:
        emb = segment["embedding"]
        matched_label = match_speaker(emb, speaker_memory)
        if matched_label:
            speaker_labels[(segment["start"], segment["end"])] = matched_label
        else:
            new_label = generate_new_speaker_label(existing_labels)
            existing_labels.add(new_label)
            speaker_labels[(segment["start"], segment["end"])] = new_label
            save_new_speaker(new_label, emb)
            speaker_memory.append({"label": new_label, "embedding": emb})

    # Merge WhisperX text and speaker segments
    result_with_speakers = whisperx.merge_text_and_speaker_segments(
        result["segments"],
        diarization_result["segments"]
    )

    # Assign consistent speaker labels
    for segment in result_with_speakers:
        key = (segment["start"], segment["end"])
        segment["speaker"] = speaker_labels.get(key, segment["speaker"])

    # Print results
    for segment in result_with_speakers:
        print(f"[{segment['start']:.1f}s - {segment['end']:.1f}s] {segment['speaker']}: {segment['text']}")

    save_transcript(result_with_speakers)

if __name__ == "__main__":
    AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio/chunk_0.wav") 
    transcribe_and_diarize(AUDIO_DIR, HF_TOKEN)