import asyncio
import time
import math
import os
import numpy as np
from dotenv import load_dotenv
#from livekit import rtc
from livekit import rtc, agents
from livekit.api import AccessToken, VideoGrants
from livekit.plugins import silero

load_dotenv()

SAMPLE_RATE = 48000
CHANNELS = 1
ECHO_DELAY = 1.0
SILENCE_TIMEOUT = 20.0


class EchoAgent:
    def __init__(self):
        self.is_user_speaking = False
        self.is_agent_speaking = False
        self.last_speech_time = None  # None until first participant joins
        self.audio_buffer = []
        self.echo_task = None
        self.participant_joined = False

    async def start(self, room: rtc.Room):
        print("🤖 Agent started, setting up audio track...")

        # Create audio source and publish it
        source = rtc.AudioSource(SAMPLE_RATE, CHANNELS)
        track = rtc.LocalAudioTrack.create_audio_track("echo-track", source)
        pub_options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        await room.local_participant.publish_track(track, pub_options)
        print("✅ Audio track published")

        # Load VAD
        vad = silero.VAD.load()
        print("✅ VAD loaded")
        print("🎧 Waiting for someone to join the room...")

        # Handle tracks already in the room
        for participant in room.remote_participants.values():
            for pub in participant.track_publications.values():
                if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                    print(f"📡 Found existing audio track from {participant.identity}")
                    self._on_participant_joined()
                    asyncio.ensure_future(self._process_track(pub.track, source, vad))

        # Handle new participant joining
        @room.on("participant_connected")
        def on_participant_connected(participant):
            print(f"👤 Participant joined: {participant.identity}")
            self._on_participant_joined()

        # Handle new tracks being published
        @room.on("track_subscribed")
        def on_track_subscribed(track, publication, participant):
            print(f"📡 Audio track received from {participant.identity}")
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                self._on_participant_joined()
                asyncio.ensure_future(self._process_track(track, source, vad))

        # Start silence checker
        asyncio.ensure_future(self._silence_checker(source))

        # Keep alive
        while True:
            await asyncio.sleep(1)

    def _on_participant_joined(self):
        """Called when a real user joins — start the silence timer from now."""
        if not self.participant_joined:
            self.participant_joined = True
            self.last_speech_time = time.time()
            print("✅ Participant detected — silence timer started")

    async def _process_track(self, track: rtc.Track, source: rtc.AudioSource, vad):
        print("🎙️ Processing audio track...")
        audio_stream = rtc.AudioStream(track, sample_rate=SAMPLE_RATE, num_channels=CHANNELS)
        vad_stream = vad.stream()

        async def feed_audio():
            async for event in audio_stream:
                frame = event.frame
                vad_stream.push_frame(frame)
                self.audio_buffer.append(frame)

        async def read_vad():
            async for event in vad_stream:
                #if event.type == silero.VAD.EventType.START_OF_SPEECH:
                if event.type == agents.vad.VADEventType.START_OF_SPEECH:
                    print("🎤 User started speaking")
                    self.is_user_speaking = True
                    self.last_speech_time = time.time()
                    # Cancel any ongoing echo immediately
                    if self.echo_task and not self.echo_task.done():
                        self.echo_task.cancel()
                        print("⛔ Echo cancelled — user is speaking")
                elif event.type == agents.vad.VADEventType.END_OF_SPEECH:
                #elif event.type == silero.VAD.EventType.END_OF_SPEECH:
                    print("🔇 User stopped speaking")
                    self.is_user_speaking = False
                    self.last_speech_time = time.time()
                    frames = list(self.audio_buffer)
                    self.audio_buffer.clear()
                    if frames:
                        self.echo_task = asyncio.ensure_future(
                            self._echo(frames, source)
                        )

        await asyncio.gather(feed_audio(), read_vad())

    async def _echo(self, frames, source: rtc.AudioSource):
        try:
            print(f"⏳ Waiting {ECHO_DELAY}s before echo...")
            await asyncio.sleep(ECHO_DELAY)

            if self.is_user_speaking:
                print("👤 User speaking — skip echo")
                return

            print(f"🔊 Echoing {len(frames)} frames...")
            self.is_agent_speaking = True

            for frame in frames:
                if self.is_user_speaking:
                    print("⛔ Interrupted during echo")
                    break
                await source.capture_frame(frame)

            print("✅ Echo done")
        except asyncio.CancelledError:
            print("🚫 Echo task cancelled")
        finally:
            self.is_agent_speaking = False

    async def _silence_checker(self, source: rtc.AudioSource):
        print("⏰ Silence checker running (waiting for participant first)...")
        while True:
            await asyncio.sleep(5)

            # Don't fire until a participant has actually joined
            if not self.participant_joined or self.last_speech_time is None:
                continue

            elapsed = time.time() - self.last_speech_time
            if elapsed >= SILENCE_TIMEOUT and not self.is_user_speaking and not self.is_agent_speaking:
                print("🔔 No speech for 20s — playing reminder tone")
                await self._play_tone(source)
                self.last_speech_time = time.time()

    async def _play_tone(self, source: rtc.AudioSource):
        self.is_agent_speaking = True
        duration = 1.0
        freq = 440
        num_samples = int(SAMPLE_RATE * duration)
        samples = np.array([
            int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
            for i in range(num_samples)
        ], dtype=np.int16)

        chunk_size = SAMPLE_RATE // 100  # 10ms chunks
        for i in range(0, len(samples) - chunk_size, chunk_size):
            if self.is_user_speaking:
                break
            chunk = samples[i:i + chunk_size]
            frame = rtc.AudioFrame(
                data=chunk.tobytes(),
                sample_rate=SAMPLE_RATE,
                num_channels=CHANNELS,
                samples_per_channel=chunk_size
            )
            await source.capture_frame(frame)

        self.is_agent_speaking = False
        print("🔔 Tone done")


async def main():
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not url or not api_key or not api_secret:
        print("❌ Missing environment variables! Check your .env file")
        return

    token = (
        AccessToken(api_key, api_secret)
        .with_identity("echo-agent")
        .with_name("Echo Agent")
        .with_grants(VideoGrants(room_join=True, room="playground-Vlyq-eIAu"))
        .to_jwt()
    )

    room = rtc.Room()

    @room.on("disconnected")
    def on_disconnected(*args):
        print("❌ Disconnected from room")

    @room.on("connected")
    def on_connected():
        print("✅ Connected to LiveKit room!")

    print(f"🔌 Connecting to {url}...")
    await room.connect(url, token)

    agent = EchoAgent()
    await agent.start(room)


if __name__ == "__main__":
    asyncio.run(main())