def test_module_public_builders_exist() -> None:
    from voxkeep.modules.audio_engine.public import AudioEngine, build_audio_engine
    from voxkeep.modules.capture.public import (
        build_capture_detection_workers,
        build_capture_module,
    )
    from voxkeep.modules.injection.public import build_injection_module
    from voxkeep.modules.storage.public import build_storage_module
    from voxkeep.modules.transcription.public import build_transcription_module

    assert AudioEngine
    assert all(
        callable(builder)
        for builder in (
            build_audio_engine,
            build_capture_detection_workers,
            build_capture_module,
            build_injection_module,
            build_storage_module,
            build_transcription_module,
        )
    )
