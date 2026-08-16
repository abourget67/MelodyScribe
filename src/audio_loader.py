"""Audio file loading and metadata extraction."""

import librosa
from pathlib import Path
from typing import Tuple


class AudioLoader:
    """Load and process audio files."""
    
    @staticmethod
    def load_audio(file_path: str) -> Tuple[str, int, float]:
        """
        Load an audio file and extract metadata.
        
        Args:
            file_path: Path to audio file (MP3, WAV, etc.)
            
        Returns:
            Tuple of (file_name, sample_rate, duration_in_seconds)
            
        Raises:
            FileNotFoundError: If the audio file doesn't exist
            ValueError: If the file format is not supported
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        if path.suffix.lower() not in ['.mp3', '.wav', '.m4a', '.flac', '.ogg']:
            raise ValueError(f"Unsupported audio format: {path.suffix}")
        
        try:
            # Load audio file with librosa
            audio_data, sr = librosa.load(file_path, sr=None)
            
            # Calculate duration in seconds
            duration = librosa.get_duration(y=audio_data, sr=sr)
            
            return path.name, sr, duration
            
        except Exception as e:
            raise ValueError(f"Error loading audio file: {str(e)}")
    
    @staticmethod
    def print_audio_info(file_path: str) -> None:
        """
        Load an audio file and print its metadata.
        
        Args:
            file_path: Path to audio file
        """
        file_name, sample_rate, duration = AudioLoader.load_audio(file_path)
        
        minutes = int(duration // 60)
        seconds = duration % 60
        
        print(f"\n📁 File: {file_name}")
        print(f"🎵 Sample Rate: {sample_rate:,} Hz")
        print(f"⏱️  Duration: {minutes}m {seconds:.2f}s ({duration:.2f}s total)\n")
