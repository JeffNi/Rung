import os
from dotenv import load_dotenv
import asyncio
import platform
from diurize import transcribe_and_diarize
from queue import Queue
from listener import AUDIO_DIR, delete_all_files, listen_for_chunk, save_chunk_to_wav
from diurize import transcribe_and_diarize

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

os.makedirs(AUDIO_DIR, exist_ok=True)

load_dotenv()
HF_TOKEN = os.environ.get("HF_TOKEN")

async def listen(queue: asyncio.Queue):
    i = 0
    while True:
        try:
            print("🔁 Starting listen_for_chunk()")
            for chunk in listen_for_chunk():
                filename = os.path.join(AUDIO_DIR, f"chunk_{i}.wav")
                save_chunk_to_wav(chunk, filename)
                print(f"🎙️ Captured chunk {i}, putting in queue")
                await queue.put(filename)
                await asyncio.sleep(0)  # yield control
                i += 1
            print("🔄 listen_for_chunk ended, restarting...")
        except Exception as e:
            print(f"❌ Error in listen(): {e}")
            await asyncio.sleep(1)


async def transcribe_worker(queue: asyncio.Queue, hf_token):
    while True:
        try:
            print("Starting Transcribe")
            filename = await queue.get()
            print(f"🔊 Got file {filename} for transcription")
            # Run transcription in thread so it doesn't block event loop
            await asyncio.to_thread(transcribe_and_diarize, filename, hf_token)
            queue.task_done()
        except Exception as e:
            print(f"❌ Error in transcribe(): {e}")
            await asyncio.sleep(1)

async def main():
    queue = asyncio.Queue()

    delete_all_files(AUDIO_DIR)

    listener_task = asyncio.create_task(listen(queue))
    transcriber_task = asyncio.create_task(transcribe_worker(queue, HF_TOKEN))

    await listener_task  # or some stopping condition
    await queue.join()   # wait until all audio chunks are processed

if __name__ == "__main__":
    asyncio.run(main())
