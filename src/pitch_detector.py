"""Pitch detection and melody extraction."""

import numpy as np
import librosa
from pathlib import Path
from typing import Tuple, Optional
import soundfile as sf


class PitchDetector:
    """Detect pitch (fundamental frequency) from audio."""
    
    def __init__(self, hop_length: int = 512, fmin: float = 80, fmax: float = 400):
        """
        Initialize the pitch detector.
        
        Args:
            hop_length: Number of samples between frames
            fmin: Minimum frequency to consider (Hz) - typical vocal range starts here
            fmax: Maximum frequency to consider (Hz) - typical vocal range ends here
        """
        self.hop_length = hop_length
        self.fmin = fmin
        self.fmax = fmax
    
    def detect_pitch(self, audio_path: str, threshold: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect pitch from audio file.
        
        Args:
            audio_path: Path to audio file
            threshold: Confidence threshold for pitch detection (0-1)
            
        Returns:
            Tuple of (times, frequencies) where:
            - times: Time in seconds for each frame
            - frequencies: Detected frequency in Hz (0 if unvoiced)
        """
        # Load audio
        print(f"\n🎤 Detecting pitch from: {Path(audio_path).name}")
        y, sr = librosa.load(audio_path, sr=None)
        print(f"   Loaded: {sr} Hz, {len(y):,} samples ({len(y)/sr:.2f}s)")
        
        # Compute pitch using piptrack (probabilistic pitch tracking)
        print(f"\n⚙️  Extracting pitch contour...")
        f0, voiced_probs = librosa.piptrack(
            y=y,
            sr=sr,
            hop_length=self.hop_length,
            fmin=self.fmin,
            fmax=self.fmax,
            threshold=threshold
        )
        
        # Extract the pitch for each frame (take the bin with highest probability)
        pitches = np.zeros(f0.shape[1])
        confidences = np.zeros(f0.shape[1])
        
        for t in range(f0.shape[1]):
            # Find the frequency bin with highest confidence
            index = voiced_probs[:, t].argmax()
            pitch = f0[index, t]
            confidence = voiced_probs[index, t]
            
            pitches[t] = pitch
            confidences[t] = confidence
        
        # Convert frame indices to time (in seconds)
        times = librosa.frames_to_time(np.arange(len(pitches)), sr=sr, hop_length=self.hop_length)
        
        # Clean up: zero out low-confidence frames
        low_confidence = confidences < threshold
        pitches[low_confidence] = 0
        
        # Additional cleanup: remove isolated pitch spikes (single frames with very different pitch)
        clean_pitches = self._smooth_pitch_contour(pitches)
        
        print(f"   ✓ Detected {np.count_nonzero(clean_pitches)} voiced frames out of {len(clean_pitches)}")
        
        return times, clean_pitches
    
    def _smooth_pitch_contour(self, pitches: np.ndarray, window_size: int = 5) -> np.ndarray:
        """
        Smooth pitch contour by removing isolated spikes and applying median filter.
        
        Args:
            pitches: Pitch values (Hz)
            window_size: Size of median filter window
            
        Returns:
            Smoothed pitch contour
        """
        from scipy.signal import medfilt
        
        # Apply median filter to smooth
        smoothed = medfilt(pitches, kernel_size=window_size)
        
        # Remove single-frame spikes: if pitch changes dramatically, set to 0
        for i in range(1, len(smoothed) - 1):
            if smoothed[i] > 0:  # Only check voiced frames
                prev_pitch = smoothed[i-1]
                next_pitch = smoothed[i+1]
                
                # If neighbors are unvoiced and this frame is voiced, likely a spike
                if prev_pitch == 0 and next_pitch == 0:
                    smoothed[i] = 0
        
        return smoothed
    
    def hz_to_midi(self, frequency: float) -> float:
        """Convert frequency in Hz to MIDI note number."""
        if frequency <= 0:
            return 0
        return 12 * np.log2(frequency / 440.0) + 69
    
    def midi_to_hz(self, midi_note: float) -> float:
        """Convert MIDI note number to frequency in Hz."""
        return 440.0 * 2 ** ((midi_note - 69) / 12)
    
    def get_note_name(self, midi_note: int) -> str:
        """Convert MIDI note to note name (e.g., C4, D#4)."""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = note_names[midi_note % 12]
        return f"{note}{octave}"
    
    def print_pitch_contour(self, times: np.ndarray, frequencies: np.ndarray, 
                           voiced_threshold: float = 10) -> None:
        """
        Print a summary of the detected pitch contour.
        
        Args:
            times: Time in seconds for each frame
            frequencies: Detected frequencies in Hz
            voiced_threshold: Minimum frequency to consider voiced
        """
        voiced = frequencies > voiced_threshold
        voiced_freqs = frequencies[voiced]
        
        if len(voiced_freqs) == 0:
            print("❌ No voiced frames detected")
            return
        
        min_freq = np.min(voiced_freqs)
        max_freq = np.max(voiced_freqs)
        mean_freq = np.mean(voiced_freqs)
        
        min_midi = self.hz_to_midi(min_freq)
        max_midi = self.hz_to_midi(max_freq)
        mean_midi = self.hz_to_midi(mean_freq)
        
        print(f"\n📊 Pitch Detection Results:")
        print(f"   Voiced frames: {np.count_nonzero(voiced)}/{len(frequencies)}")
        print(f"   Frequency range: {min_freq:.1f} - {max_freq:.1f} Hz")
        print(f"   Mean frequency: {mean_freq:.1f} Hz")
        print(f"   Vocal range (MIDI): {self.get_note_name(int(min_midi))} - {self.get_note_name(int(max_midi))}")
        print(f"   Mean MIDI: {mean_midi:.1f} ({self.get_note_name(int(mean_midi))})\n")
    
    def save_pitch_plot(self, audio_path: str, times: np.ndarray, frequencies: np.ndarray,
                        output_dir: Optional[str] = None) -> str:
        """
        Save a visualization of the pitch contour.
        
        Args:
            audio_path: Path to original audio file
            times: Time in seconds for each frame
            frequencies: Detected frequencies in Hz
            output_dir: Directory to save plot (default: same as audio file)
            
        Returns:
            Path to saved plot image
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("⚠️  matplotlib not installed. Run: pip install matplotlib")
            return ""
        
        input_path = Path(audio_path)
        if output_dir is None:
            output_dir = input_path.parent
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 4))
        
        # Plot pitch contour
        ax.plot(times, frequencies, linewidth=1.5, color='#1f77b4', label='Pitch')
        
        # Highlight voiced frames
        voiced = frequencies > 10
        ax.scatter(times[voiced], frequencies[voiced], s=20, color='#ff7f0e', alpha=0.6, label='Voiced')
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Frequency (Hz)')
        ax.set_title(f'Pitch Contour: {input_path.name}')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_ylim(0, 500)
        
        # Save
        plot_path = output_dir / f"{input_path.stem}_pitch_plot.png"
        plt.savefig(plot_path, dpi=100, bbox_inches='tight')
        plt.close()
        
        print(f"💾 Saved plot: {plot_path.name}")
        return str(plot_path)
    
    def save_pitch_csv(self, times: np.ndarray, frequencies: np.ndarray,
                       output_path: str) -> None:
        """
        Save pitch contour as CSV.
        
        Args:
            times: Time in seconds for each frame
            frequencies: Detected frequencies in Hz
            output_path: Path to save CSV file
        """
        import csv
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time_s', 'frequency_hz', 'midi_note', 'note_name'])
            
            for t, freq in zip(times, frequencies):
                if freq > 0:
                    midi = self.hz_to_midi(freq)
                    note = self.get_note_name(int(midi))
                    writer.writerow([f"{t:.4f}", f"{freq:.2f}", f"{midi:.2f}", note])
                else:
                    writer.writerow([f"{t:.4f}", "0", "-", ""])
        
        print(f"💾 Saved CSV: {output_path.name}")
