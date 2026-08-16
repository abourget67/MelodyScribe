"""PitchCraft - Main entry point."""

import sys
from pathlib import Path
from audio_loader import AudioLoader
from vocal_separator import VocalSeparator
from pitch_detector import PitchDetector
from note_segmenter import NoteSegmenter
from musicxml_converter import MusicXMLConverter


def print_usage():
    """Print usage information."""
    print("\nPitchCraft - Vocal Melody Extraction\n")
    print("Usage:")
    print("  python main.py info <path_to_audio>              # Show audio metadata")
    print("  python main.py separate <path_to_audio>         # Extract vocals")
    print("  python main.py detect-pitch <path_to_audio>     # Detect pitch from vocals")
    print("  python main.py segment-notes <path_to_audio>    # Segment pitch into notes")
    print("  python main.py convert-musicxml <path_to_audio> # Convert notes to MusicXML")
    print("  python main.py convert-pdf <path_to_audio>      # Render MusicXML as PDF sheet music\n")
    print("Supported formats: MP3, WAV, M4A, FLAC, OGG\n")


def main():
    """Main entry point for PitchCraft."""
    
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    audio_file = sys.argv[2]
    
    try:
        if command == "info":
            AudioLoader.print_audio_info(audio_file)
        
        elif command == "separate":
            separator = VocalSeparator()
            vocal_path, instrumental_path = separator.separate(audio_file)
            print(f"✅ Separation complete!")
            print(f"   Vocals: {vocal_path}")
            print(f"   Instrumental: {instrumental_path}")
        
        elif command == "detect-pitch":
            detector = PitchDetector()
            times, frequencies = detector.detect_pitch(audio_file)
            detector.print_pitch_contour(times, frequencies)
            
            # Save outputs
            output_dir = Path(audio_file).parent / "pitch_analysis"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save CSV
            csv_path = output_dir / f"{Path(audio_file).stem}_pitch.csv"
            detector.save_pitch_csv(times, frequencies, str(csv_path))
            
            # Save plot
            detector.save_pitch_plot(audio_file, times, frequencies, str(output_dir))
            
            print(f"✅ Pitch detection complete!")
        
        elif command == "segment-notes":
            # First detect pitch if not already done
            pitch_csv = Path(audio_file).parent / "pitch_analysis" / f"{Path(audio_file).stem}_pitch.csv"
            
            if not pitch_csv.exists():
                print("⚠️  Pitch not yet detected. Running pitch detection first...")
                detector = PitchDetector()
                times, frequencies = detector.detect_pitch(audio_file)
                detector.save_pitch_csv(times, frequencies, str(pitch_csv))
            
            # Segment notes
            segmenter = NoteSegmenter()
            notes = segmenter.segment_from_pitch_csv(str(pitch_csv), audio_file)
            
            if notes:
                segmenter.print_notes(notes)
                
                # Save outputs
                output_dir = Path(audio_file).parent / "note_segmentation"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Save JSON
                json_path = output_dir / f"{Path(audio_file).stem}_notes.json"
                segmenter.save_notes_json(notes, str(json_path))
                
                # Save MIDI
                midi_path = output_dir / f"{Path(audio_file).stem}_notes.mid"
                segmenter.save_notes_midi(notes, str(midi_path))
                
                print(f"✅ Note segmentation complete!")
            else:
                print("❌ No notes detected")
        
        elif command == "convert-musicxml":
            # Find or create notes
            notes_json = Path(audio_file).parent / "note_segmentation" / f"{Path(audio_file).stem}_notes.json"
            
            if not notes_json.exists():
                print("⚠️  Notes not yet segmented. Running full pipeline...")
                
                # Run pitch detection if needed
                pitch_csv = Path(audio_file).parent / "pitch_analysis" / f"{Path(audio_file).stem}_pitch.csv"
                if not pitch_csv.exists():
                    print("   → Detecting pitch...")
                    detector = PitchDetector()
                    times, frequencies = detector.detect_pitch(audio_file)
                    detector.save_pitch_csv(times, frequencies, str(pitch_csv))
                
                # Run note segmentation
                print("   → Segmenting notes...")
                segmenter = NoteSegmenter()
                notes = segmenter.segment_from_pitch_csv(str(pitch_csv), audio_file)
                
                if notes:
                    output_dir = Path(audio_file).parent / "note_segmentation"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    segmenter.save_notes_json(notes, str(notes_json))
                    segmenter.save_notes_midi(notes, str(output_dir / f"{Path(audio_file).stem}_notes.mid"))
                else:
                    print("❌ No notes detected")
                    sys.exit(1)
            
            # Convert to MusicXML
            converter = MusicXMLConverter()
            output_musicxml = Path(audio_file).parent / "note_segmentation" / f"{Path(audio_file).stem}_notes.musicxml"
            converter.convert_json_to_musicxml(str(notes_json), str(output_musicxml))

        elif command == "convert-pdf":
            output_dir = Path(audio_file).parent / "note_segmentation"
            musicxml_path = output_dir / f"{Path(audio_file).stem}_notes.musicxml"
            pdf_path = output_dir / f"{Path(audio_file).stem}_notes.pdf"

            converter = MusicXMLConverter()
            converter.convert_musicxml_to_pdf(str(musicxml_path), str(pdf_path))
        
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
            sys.exit(1)
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ Runtime error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
