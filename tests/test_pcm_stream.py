from array import array

from sidpulse.audio.stream import PCMStream


def test_callback_preserves_every_sample_across_uneven_requests():
    stream = PCMStream(256, open_device=False)
    source = array('h', range(1024)).tobytes()
    for start in (0, 512):
        stream.write(source[start:start+512])
    assert not stream.priming
    result = bytearray()
    next_block = 1024
    for frames in (73, 183, 129, 127, 256, 256):
        if stream.needs_block() and next_block < len(source):
            stream.write(source[next_block:next_block+512]); next_block += 512
        target = bytearray(frames*2)
        stream.callback(None, target)
        result.extend(target)
    assert bytes(result) == source
    assert stream.gaps == stream.missing_frames == 0


def test_gap_counts_one_starvation_episode_and_recovers_without_dropping_pcm():
    stream = PCMStream(256, open_device=False)
    stream.expect_audio = True
    target = bytearray(512)
    stream.callback(None, target)
    assert stream.gaps == 0  # first prime is not a failure
    stream.write(b'\x01\x00'*256); stream.write(b'\x02\x00'*256)
    stream.callback(None, target); assert target == b'\x01\x00'*256
    stream.callback(None, target); assert target == b'\x02\x00'*256
    stream.callback(None, target); stream.callback(None, target)
    assert target == bytes(512)
    assert stream.gaps == 1 and stream.missing_frames == 512
    stream.write(b'\x03\x00'*256)
    stream.callback(None, target); assert target == b'\x03\x00'*256
    stream.callback(None, target)
    assert stream.gaps == 2
    stream.reset_stats(); assert stream.gaps == stream.missing_frames == 0
    stream.pause(); stream.callback(None, target); assert stream.gaps == 0
    stream.stop(); assert stream.priming and not stream.blocks
