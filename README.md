# MelodyScribe

A Mac application for extracting lead vocal melody from audio files and generating MusicXML and MIDI.

## Project Goals

Extract vocal melody → detect pitch → segment notes → generate MusicXML/MIDI

## Milestones

### Milestone 1: Audio Loading ✓
- [x] Load MP3/WAV files
- [x] Extract sample rate and duration

### Milestone 2: Vocal Separation ✓
- [x] Integrate Demucs for vocal extraction
- [x] Separate vocals from instrumental
- [x] Save separated stems as WAV files

### Milestone 3: Pitch Detection ✓
- [x] Detect fundamental frequency from vocal track
- [x] Extract pitch contour over time
- [x] Save results as CSV and visualization

### Milestone 4: Note Segmentation ✓
- [x] Identify note onsets and offsets
- [x] Extract individual notes with timing and velocity
- [x] Export to JSON and MIDI formats

### Milestone 5: MusicXML Generation ✓
- [x] Convert notes to MusicXML format
- [x] Support standard notation software (MuseScore, Finale, Dorico)
- [x] End-to-end pipeline complete

## Project Structure

```
MelodyScribe/
├── src/
│   ├── __init__.py
│   ├── audio_loader.py      # Audio file loading utilities
│   ├── vocal_separator.py   # Vocal extraction
│   ├── pitch_detector.py    # Pitch detection and melody extraction
│   └── main.py             # Entry point
├── tests/
│   └── test_audio_loader.py
├── samples/                 # Sample audio files for testing
├── requirements.txt
├── README.md
└── .gitignore

## Usage

### Show audio metadata
```bash
cd src
python3 main.py info ../samples/your_audio.mp3
```

Output:
```
📁 File: your_audio.mp3
🎵 Sample Rate: 44,100 Hz
⏱️  Duration: 3m 45.50s (225.50s total)
```

### Extract vocals from instrumental
```bash
python3 main.py separate ../samples/your_audio.mp3
```

Output:
```
✅ Separation complete!
   Vocals: ../samples/separated/your_audio_vocals.wav
   Instrumental: ../samples/separated/your_audio_instrumental.wav
```

The separated files are saved in `samples/separated/`

### Detect pitch (melody) from vocals
```bash
python3 main.py detect-pitch ../samples/separated/sample_vocals.wav
```

Output:
```
🎤 Detecting pitch from: sample_vocals.wav
   Loaded: 44100 Hz, 6,947,759 samples (157.55s)

⚙️  Extracting pitch contour...
   ✓ Detected 10093 voiced frames out of 13570

📊 Pitch Detection Results:
   Voiced frames: 10093/13570
   Frequency range: 82.2 - 397.9 Hz
   Mean frequency: 264.7 Hz
   Vocal range (MIDI): D#2 - G4
   Mean MIDI: 60.2 (C4)

💾 Saved CSV: sample_vocals_pitch.csv
💾 Saved plot: sample_vocals_pitch_plot.png
✅ Pitch detection complete!
```

Generated files:
- `pitch_analysis/sample_vocals_pitch.csv` - Pitch values with MIDI notes
- `pitch_analysis/sample_vocals_pitch_plot.png` - Visualization of the pitch contour

### Segment pitch into individual notes
```bash
python3 main.py segment-notes ../samples/separated/sample_vocals.wav
```

Output:
```
🎼 Segmenting notes from pitch contour...
   ✓ Found 162 notes

📋 Note Sequence:
#    Time         Duration   Note     Freq       Velocity
------------------------------------------------------------
1    12.411s    0.174s      E4    332.8Hz      19
2    12.608s    0.128s      E4    333.4Hz      30
...
```

Generated files:
- `note_segmentation/sample_vocals_notes.json` - Note sequence with timing
- `note_segmentation/sample_vocals_notes.mid` - MIDI file

### Convert to MusicXML for notation software
```bash
python3 main.py convert-musicxml ../samples/separated/sample_vocals.wav
```

Output:
```
🎼 Converting to MusicXML...
   ℹ️  162 notes loaded
✅ Saved MusicXML: sample_vocals_notes.musicxml
✅ MusicXML conversion complete!
```

Generated file:
- `note_segmentation/sample_vocals_notes.musicxml` - MusicXML notation (compatible with MuseScore, Finale, Dorico, etc.)

## Installation

```bash
python3 -m pip install -r requirements.txt
```

Dependencies:
- `librosa` - Audio processing
- `numpy` - Numerical computing  
- `soundfile` - Audio I/O
- `scipy` - Scientific computing (signal processing)
- `matplotlib` - Visualization and plotting
- `music21` - MusicXML generation
- `torch` / `torchaudio` - PyTorch and audio utilities
- `demucs` - Vocal separation (Facebook's source separation model)
