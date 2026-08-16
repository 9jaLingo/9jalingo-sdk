import io
import unittest

import httpx

from naijalingo._client import _BaseClient
from naijalingo.tts import TTS


class CloneResponseTests(unittest.TestCase):
    def setUp(self):
        self.requests = []

        def handler(request):
            self.requests.append(request)
            if request.url.path == "/v1/audio/clone":
                return httpx.Response(
                    200,
                    content=b"RIFFcloned-audio",
                    headers={
                        "content-type": "audio/wav",
                        "X-Voice-ID": "voice-uuid-123",
                        "X-Voice-Code": "my-cloned-voice",
                        "X-Voice-Name": "My Cloned Voice",
                        "X-Clone-ID": "clone-uuid-456",
                        "X-Job-ID": "job-uuid-789",
                    },
                )
            return httpx.Response(
                200,
                content=b"RIFFgenerated-audio",
                headers={"content-type": "audio/wav"},
            )

        client = _BaseClient(api_key="test-key", base_url="https://api.test")
        client._client.close()
        client._client = httpx.Client(
            base_url="https://api.test",
            headers={"X-API-Key": "test-key"},
            transport=httpx.MockTransport(handler),
        )
        self.tts = TTS(client)

    def test_clone_returns_reusable_voice_metadata(self):
        reference_audio = io.BytesIO(b"reference-audio")
        reference_audio.name = "reference.wav"

        clone = self.tts.clone("Hello from my clone", reference_audio, voice="pcm")

        self.assertEqual(clone.content, b"RIFFcloned-audio")
        self.assertEqual(clone.voice_id, "voice-uuid-123")
        self.assertEqual(clone.voice_code, "my-cloned-voice")
        self.assertEqual(clone.voice_name, "My Cloned Voice")
        self.assertEqual(clone.clone_id, "clone-uuid-456")
        self.assertEqual(clone.job_id, "job-uuid-789")

        generated_audio = self.tts.generate("Use the cloned voice", voice=clone.voice_id)
        self.tts.generate("Use the cloned speaker", speaker=clone.voice_id)

        self.assertEqual(len(generated_audio), len(b"RIFFgenerated-audio"))
        generated_bodies = [
            request.read().decode()
            for request in self.requests
            if request.url.path == "/v1/audio/speech"
        ]
        self.assertEqual(len(generated_bodies), 2)
        self.assertTrue(all('"voice":"voice-uuid-123"' in body for body in generated_bodies))


if __name__ == "__main__":
    unittest.main()