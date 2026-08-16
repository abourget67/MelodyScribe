"""
MusicXML converter for exporting extracted vocal melody.

Converts note sequences to MusicXML format for use in notation software
(MuseScore, Finale, Dorico, etc.).
"""

import json
from pathlib import Path
from typing import List
from dataclasses import dataclass

from music21 import stream, instrument, meter, tempo, note, metadata


@dataclass
class Note:
    """Represents a single musical note."""
    start_time: float
    end_time: float
    duration: float
    frequency: float
    midi_note: int
    note_name: str
    velocity: int


class MusicXMLConverter:
    """Convert note sequences to MusicXML format."""
    
    def __init__(self, tempo_bpm: int = 120):
        """
        Initialize the MusicXML converter.
        
        Args:
            tempo_bpm: Tempo in beats per minute (default 120)
        """
        self.tempo_bpm = tempo_bpm
    
    def notes_from_json(self, json_path: str) -> tuple[List[Note], dict]:
        """
        Load notes from JSON file.
        
        Args:
            json_path: Path to notes JSON file
            
        Returns:
            Tuple of (notes list, metadata dict)
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        notes = []
        for note_data in data.get('notes', []):
            notes.append(Note(
                start_time=note_data['start_time'],
                end_time=note_data['end_time'],
                duration=note_data['duration'],
                frequency=note_data['frequency'],
                midi_note=note_data['midi_note'],
                note_name=note_data['note_name'],
                velocity=note_data['velocity']
            ))
        
        metadata_dict = {
            'num_notes': data.get('num_notes'),
            'total_duration': data.get('total_duration')
        }
        
        return notes, metadata_dict
    
    def create_musicxml(
        self,
        notes: List[Note],
        title: str = "Vocal Melody",
        composer: str = "MelodyScribe",
        time_signature: tuple = (4, 4)
    ) -> stream.Score:
        """
        Create a music21 Score object from note sequence.
        
        Args:
            notes: List of Note objects
            title: Score title
            composer: Composer name
            time_signature: Time signature as (numerator, denominator)
            
        Returns:
            music21 Score object
        """
        # Create score and part
        score = stream.Score()
        part = stream.Part()
        
        # Add instrument (voice)
        part.append(instrument.Vocalist())
        
        # Add metadata
        score.metadata = metadata.Metadata()
        score.metadata.title = title
        score.metadata.composer = composer
        
        # Add time signature
        part.append(meter.TimeSignature(f'{time_signature[0]}/{time_signature[1]}'))
        
        # Add tempo
        part.append(tempo.MetronomeMark(number=self.tempo_bpm))
        
        if not notes:
            score.append(part)
            return score
        
        # Convert time-based notes to music21 notes
        # Need to establish beat duration from tempo
        beats_per_second = self.tempo_bpm / 60.0
        
        for note_obj in notes:
            # Calculate quarter note duration
            duration_quarters = note_obj.duration * beats_per_second / 4.0
            
            # Quantize to valid MusicXML durations
            # Valid values: 0.25, 0.5, 1.0, 2.0, 4.0, etc. (powers of 2 times 0.25)
            # Find the closest valid duration
            valid_durations = [0.25, 0.5, 1.0, 1.5, 2.0, 4.0, 8.0]
            closest_duration = min(valid_durations, key=lambda x: abs(x - duration_quarters))
            
            # Create music21 note
            n = note.Note()
            n.pitch.midi = note_obj.midi_note
            n.quarterLength = closest_duration
            
            # Add velocity if available
            if note_obj.velocity > 0:
                n.volume.velocity = int(note_obj.velocity * 127 / 100)
            
            part.append(n)
        
        score.append(part)
        return score
    
    def save_musicxml(self, score: stream.Score, output_path: str) -> None:
        """
        Save Score to MusicXML file.
        
        Args:
            score: music21 Score object
            output_path: Path to save MusicXML file (.musicxml extension)
        """
        score.write('musicxml', fp=output_path)
        print(f"✅ Saved MusicXML: {Path(output_path).name}")
    
    def convert_json_to_musicxml(
        self,
        json_path: str,
        output_path: str,
        title: str = "Vocal Melody",
        composer: str = "MelodyScribe"
    ) -> None:
        """
        Convert JSON note file directly to MusicXML.
        
        Args:
            json_path: Path to input JSON notes file
            output_path: Path to output MusicXML file
            title: Score title
            composer: Composer name
        """
        print(f"🎼 Converting to MusicXML...")
        
        # Load notes from JSON
        notes, metadata_dict = self.notes_from_json(json_path)
        print(f"   ℹ️  {metadata_dict['num_notes']} notes loaded")
        
        # Create score
        score = self.create_musicxml(notes, title=title, composer=composer)
        
        # Save MusicXML
        self.save_musicxml(score, output_path)
        print(f"✅ MusicXML conversion complete!")
    
    def convert_midi_to_musicxml(
        self,
        midi_path: str,
        output_path: str,
        title: str = "Vocal Melody",
        composer: str = "MelodyScribe"
    ) -> None:
        """
        Convert MIDI file to MusicXML.
        
        Args:
            midi_path: Path to input MIDI file
            output_path: Path to output MusicXML file
            title: Score title
            composer: Composer name
        """
        print(f"🎼 Converting MIDI to MusicXML...")
        
        # Load MIDI
        score = stream.Score()
        score = score.read(midi_path)
        
        # Update metadata
        if not score.metadata:
            score.metadata = metadata.Metadata()
        score.metadata.title = title
        score.metadata.composer = composer
        
        # Save MusicXML
        self.save_musicxml(score, output_path)
        print(f"✅ MusicXML conversion complete!")
