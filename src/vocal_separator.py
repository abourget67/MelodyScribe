"""Vocal separation using Demucs."""

import numpy as np
from pathlib import Path
from typing import Tuple
import warnings

try:
    from demucs.pretrained import get_model
    from demucs.audio import convert_audio
    DEMUCS_AVAILABLE = True
except ImportError:
    DEMUCS_AVAILABLE = False


class VocalSeparator:
    """Separate vocals from instrumental using Demucs."""
    
    def __init__(self, model_name: str = "htdemucs", device: str = "cpu"):
        """
        Initialize the vocal separator.
        
        Args:
            model_name: Demucs model to use ("htdemucs", "demucs", etc.)
            device: "cpu" or "cuda" (cuda requires GPU)
        """
        if not DEMUCS_AVAILABLE:
            raise ImportError(
                "Demucs is not installed. Install with: python3 -m pip install -r requirements.txt"
            )
        
        self.model_name = model_name
        self.device = device
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Demucs model."""
        print(f"Loading {self.model_name} model on {self.device}...")
        self.model = get_model(self.model_name)
        self.model.to(self.device)
        self.model.eval()
        print("✓ Model loaded")
    
    def separate(self, audio_path: str, output_dir: str = None) -> Tuple[str, str]:
        """
        Separate vocals from instrumental.
        
        Args:
            audio_path: Path to input audio file
            output_dir: Directory to save separated stems (default: input_dir/separated)
            
        Returns:
            Tuple of (vocal_path, instrumental_path)
        """
        import torchaudio
        import torch
        from demucs.apply import apply_model
        
        input_path = Path(audio_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Set output directory
        if output_dir is None:
            output_dir = input_path.parent / "separated"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load audio
        print(f"\n🎵 Loading audio: {input_path.name}")
        waveform, sr = torchaudio.load(str(input_path))
        
        channels, frames = waveform.shape
        print(f"   Loaded: {channels} channel(s), {frames:,} frames at {sr} Hz")
        
        # Ensure stereo (model expects 2 channels)
        if waveform.shape[0] == 1:
            print(f"   Converting mono to stereo...")
            waveform = waveform.repeat(2, 1)
        elif waveform.shape[0] > 2:
            print(f"   Downmixing to stereo...")
            waveform = waveform[:2]
        
        # Resample if needed
        if sr != self.model.samplerate:
            print(f"   Resampling to {self.model.samplerate} Hz...")
            resampler = torchaudio.transforms.Resample(sr, self.model.samplerate)
            waveform = resampler(waveform)
        
        # Apply separation
        print(f"\n⚙️  Separating vocals from instrumental...")
        
        # Add batch dimension if needed (model expects [batch, channels, samples])
        if waveform.dim() == 2:
            waveform = waveform.unsqueeze(0)
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import torch
            with torch.no_grad():
                stems = apply_model(
                    self.model,
                    waveform.to(self.device)
                )
        
        # Remove batch dimension if present (stems should be [sources, channels, samples])
        if stems.dim() == 4:
            stems = stems.squeeze(0)
        
        # Extract vocal and instrumental
        # Demucs returns dict: {'vocals': tensor, 'bass': tensor, 'drums': tensor, 'other': tensor}
        if isinstance(stems, dict):
            vocals = stems['vocals']
            # Combine non-vocal stems for instrumental
            instrumental = stems['bass'] + stems['drums'] + stems['other']
        else:
            # If stems is a tensor, assume order: [drums, bass, other, vocals]
            vocals = stems[3]  # vocals stem
            instrumental = stems[0] + stems[1] + stems[2]  # drums + bass + other
        
        # Save stems
        vocal_path = output_dir / f"{input_path.stem}_vocals.wav"
        instrumental_path = output_dir / f"{input_path.stem}_instrumental.wav"
        
        print(f"\n💾 Saving stems...")
        torchaudio.save(str(vocal_path), vocals, self.model.samplerate)
        torchaudio.save(str(instrumental_path), instrumental, self.model.samplerate)
        
        print(f"   ✓ Vocals: {vocal_path.name}")
        print(f"   ✓ Instrumental: {instrumental_path.name}\n")
        
        return str(vocal_path), str(instrumental_path)
