"""Note segmentation from pitch contour."""

import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import json
import librosa
from pitch_detector import PitchDetector


@dataclass
class Note:
    """Represents a single musical note."""
    start_time: float  # seconds
    end_time: float    # seconds
    duration: float    # seconds
    frequency: float   # Hz (average of all frames)
    midi_note: int     # MIDI note number
    note_name: str     # e.g., "C4", "D#4"
    velocity: float    # 0-127 (based on energy/confidence)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'start_time': round(self.start_time, 4),
            'end_time': round(self.end_time, 4),
            'duration': round(self.duration, 4),
            'frequency': round(self.frequency, 2),
            'midi_note': self.midi_note,
            'note_name': self.note_name,
            'velocity': int(self.velocity)
        }


class NoteSegmenter:
    """Segment pitch contour into individual notes."""
    
    def __init__(self, hop_length: int = 512, sr: int = 44100,
                 min_duration: float = 0.1, freq_tolerance: float = 20):
        """
        Initialize the note segmenter.
        
        Args:
            hop_length: Samples between frames (must match pitch detector)
            sr: Sample rate
            min_duration: Minimum note duration in seconds
            freq_tolerance: Frequency tolerance for grouping frames (Hz)
        """
        self.hop_length = hop_length
        self.sr = sr
        self.min_duration = min_duration
        self.freq_tolerance = freq_tolerance
        self.pitch_detector = PitchDetector(hop_length=hop_length)
    
    def segment_pitch_contour(self, times: np.ndarray, frequencies: np.ndarray,
                             audio_path: Optional[str] = None) -> List[Note]:
        """
        Segment a pitch contour into individual notes.
        
        Args:
            times: Time array from pitch detection (seconds)
            frequencies: Frequency array from pitch detection (Hz)
            audio_path: Optional path to audio for energy analysis
            
        Returns:
            List of Note objects
        """
        print(f"\n🎼 Segmenting notes from pitch contour...")
        
        # Get energy envelope if audio path provided
        energy = None
        if audio_path:
            energy = self._compute_energy_envelope(audio_path, len(frequencies))
        
        # Find note boundaries
        notes_data = self._find_note_boundaries(times, frequencies, energy)
        
        print(f"   ✓ Found {len(notes_data)} notes")
        
        # Convert to Note objects
        notes = []
        for start_idx, end_idx, avg_freq in notes_data:
            if avg_freq > 0:  # Only voiced notes
                start_time = times[start_idx]
                end_time = times[end_idx]
                duration = end_time - start_time
                
                # Skip very short notes (likely noise)
                if duration < self.min_duration:
                    continue
                
                # Convert to MIDI
                midi_note = self.pitch_detector.hz_to_midi(avg_freq)
                note_name = self.pitch_detector.get_note_name(int(midi_note))
                
                # Estimate velocity (0-127) from average confidence if available
                velocity = 64  # Default velocity
                if energy is not None:
                    avg_energy = np.mean(energy[start_idx:end_idx])
                    velocity = min(127, max(1, int(avg_energy * 127)))
                
                note = Note(
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    frequency=avg_freq,
                    midi_note=int(midi_note),
                    note_name=note_name,
                    velocity=velocity
                )
                notes.append(note)
        
        return notes
    
    def _find_note_boundaries(self, times: np.ndarray, frequencies: np.ndarray,
                            energy: Optional[np.ndarray] = None) -> List[Tuple[int, int, float]]:
        """
        Find note boundaries in a pitch contour.
        
        Returns:
            List of (start_idx, end_idx, avg_frequency) tuples
        """
        notes = []
        in_note = False
        note_start = 0
        note_freqs = []
        
        for i, freq in enumerate(frequencies):
            # Determine if this frame is part of a note
            # A frame is voiced if: frequency > 0 AND (no energy check OR energy > threshold)
            is_voiced = freq > 0
            if energy is not None:
                is_voiced = is_voiced and energy[i] > 0.01
            
            if is_voiced:
                if not in_note:
                    # Start of a new note
                    in_note = True
                    note_start = i
                    note_freqs = [freq]
                else:
                    # Continue the current note
                    # Check if frequency is stable (within tolerance)
                    avg_freq = np.mean(note_freqs)
                    freq_diff = abs(freq - avg_freq)
                    
                    if freq_diff > self.freq_tolerance:
                        # Large frequency jump - might be a new note
                        # For now, treat it as continuation
                        pass
                    
                    note_freqs.append(freq)
            else:
                # Unvoiced frame
                if in_note:
                    # End of current note
                    avg_freq = np.mean(note_freqs)
                    notes.append((note_start, i - 1, avg_freq))
                    in_note = False
                    note_freqs = []
        
        # Handle note at end of contour
        if in_note:
            avg_freq = np.mean(note_freqs)
            notes.append((note_start, len(frequencies) - 1, avg_freq))
        
        return notes
    
    def _compute_energy_envelope(self, audio_path: str, num_frames: int) -> np.ndarray:
        """
        Compute energy envelope of audio to identify silent regions.
        
        Args:
            audio_path: Path to audio file
            num_frames: Number of frames to match pitch contour length
            
        Returns:
            Normalized energy envelope (0-1)
        """
        y, sr = librosa.load(audio_path, sr=None)
        
        # Compute STFT magnitude
        S = librosa.magphase(librosa.stft(y, n_fft=2048, hop_length=self.hop_length))[0]
        
        # Sum energy across frequency bins
        energy = np.sum(S, axis=0)
        
        # Resample to match number of frames
        if len(energy) != num_frames:
            energy = np.interp(
                np.linspace(0, len(energy) - 1, num_frames),
                np.arange(len(energy)),
                energy
            )
        
        # Normalize to 0-1
        if np.max(energy) > 0:
            energy = energy / np.max(energy)
        
        return energy
    
    def print_notes(self, notes: List[Note]) -> None:
        """Print a table of detected notes."""
        if not notes:
            print("❌ No notes detected")
            return
        
        print(f"\n📋 Note Sequence ({len(notes)} notes):")
        print(f"{'#':<4} {'Time':<12} {'Duration':<10} {'Note':<8} {'Freq':<10} {'Velocity':<8}")
        print("-" * 60)
        
        for i, note in enumerate(notes, 1):
            print(f"{i:<4} {note.start_time:>6.3f}s {note.duration:>8.3f}s "
                  f"{note.note_name:>7} {note.frequency:>8.1f}Hz {note.velocity:>7}")
    
    def save_notes_json(self, notes: List[Note], output_path: str) -> None:
        """
        Save notes to JSON file.
        
        Args:
            notes: List of Note objects
            output_path: Path to save JSON
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'num_notes': len(notes),
            'total_duration': notes[-1].end_time if notes else 0,
            'notes': [note.to_dict() for note in notes]
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Saved notes JSON: {output_path.name}")
    
    def save_notes_midi(self, notes: List[Note], output_path: str, tempo: int = 120) -> None:
        """
        Save notes as MIDI file using midiutil for reliability.
        
        Args:
            notes: List of Note objects
            output_path: Path to save MIDI
            tempo: BPM for MIDI conversion
        """
        try:
            from midiutil import MIDIFile
        except ImportError:
            print("⚠️  midiutil not installed. Install with: python3 -m pip install midiutil")
            return
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not notes:
            print("⚠️  No notes to save")
            return
        
        # Create MIDI file (1 track)
        midi = MIDIFile(1)
        track = 0
        channel = 0
        
        # Add tempo
        midi.addTempo(track, 0, tempo)
        
        # Set program/instrument to voice (program 52 = soprano sax, program 54 = voice ooh)
        # Let's use program 53 which is often a solo voice
        midi.addProgramChange(track, channel, 0, 53)
        
        # Find earliest note start time to use as reference
        min_start_time = min(n.start_time for n in notes)
        
        # Conversion factor: beats per second
        beats_per_second = tempo / 60.0
        
        # Add notes
        for note_obj in notes:
            # Convert time from seconds to quarter notes (beats)
            time_in_beats = (note_obj.start_time - min_start_time) * beats_per_second
            
            # Convert duration from seconds to quarter notes
            duration_in_beats = note_obj.duration * beats_per_second
            # Minimum duration to avoid MIDI issues
            duration_in_beats = max(0.25, duration_in_beats)
            
            # Velocity: scale from 0-100 to 1-127, then boost for audibility
            velocity = max(1, int(note_obj.velocity * 1.27))
            # Boost low velocities to ensure audibility
            velocity = max(64, velocity)  # Minimum velocity 64 for clear hearing
            
            # Add note to MIDI
            midi.addNote(
                track=track,
                channel=channel,
                pitch=int(note_obj.midi_note),
                time=time_in_beats,
                duration=duration_in_beats,
                volume=velocity
            )
        
        # Write to file
        with open(str(output_path), 'wb') as f:
            midi.writeFile(f)
        
        print(f"💾 Saved MIDI: {output_path.name}")
    
    def segment_from_pitch_csv(self, csv_path: str, audio_path: Optional[str] = None) -> List[Note]:
        """
        Segment notes from a pitch CSV file (output from pitch_detector).
        
        Args:
            csv_path: Path to pitch CSV file
            audio_path: Optional path to audio for energy analysis
            
        Returns:
            List of Note objects
        """
        import csv
        
        times = []
        frequencies = []
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                times.append(float(row['time_s']))
                freq = float(row['frequency_hz'])
                frequencies.append(freq if freq > 0 else 0)
        
        return self.segment_pitch_contour(
            np.array(times),
            np.array(frequencies),
            audio_path
        )
