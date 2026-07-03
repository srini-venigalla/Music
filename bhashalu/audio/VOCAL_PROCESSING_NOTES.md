# Vocal Processing Chain — Project Notes

**Goal:** Female lead vocal floats above the instrumental bed. Comfortable balance for living-room TV listening; vocal stays intelligible from kitchen/dining at the same volume.

**DAW:** Audacity
**Voice:** Female lead, slight nasal character

## Loudness Targets by Vocal Type

| Vocal Profile | Final Integrated LUFS |
|---------------|----------------------|
| F-dominant, crystalline (Shreya-grade) | **−17 LUFS** |
| F-dominant, full-bodied (Asha-grade) | **−16 LUFS** |
| M-dominant | **−15 LUFS** |
| Mixed F+M duet | **−16 LUFS** |
| Devotional / classical fusion | **−17 to −18 LUFS** |

**Rule:** *Vocal lustre lives in 8-15 kHz transient peaks. Limiting above streaming normalization (−14 LUFS reference) sacrifices these peaks. For F-dominant Indian playback, target −17 LUFS to preserve crystalline character. Streaming platforms normalize anyway; lustre is preserved.*

**Test:** *A/B with reference Shreya Ghoshal track at same playback level. If your master sounds duller in 8-15 kHz than reference, lower LUFS target by 1 dB and re-master.*
---

## Processing Chain (apply in order)

### 1. EQ — Filter Curve EQ

Targets nasal resonance, removes sub-rumble, adds presence and air for cross-room intelligibility.

| Frequency | Gain   | Purpose                         |
|-----------|--------|---------------------------------|
| 20 Hz     | −30 dB | High-pass roll-off              |
| 100 Hz    | 0 dB   | HPF corner                      |
| 800 Hz    | 0 dB   | Anchor (keep midrange flat)     |
| 1.2 kHz   | −4 dB  | **Nasal cut** (sweep-confirmed) |
| 2 kHz     | 0 dB   | Anchor                          |
| 3 kHz     | +2 dB  | Presence / intelligibility      |
| 5 kHz     | 0 dB   | Anchor                          |
| 10 kHz    | +3 dB  | Air shelf                       |
| 20 kHz    | +3 dB  | Air shelf                       |

### 2. Compression — Compressor

Evens out dynamics so quiet syllables stay audible across rooms.

- Threshold: **−18 dB**
- Make-up gain: **+2 dB**
- Knee width: **5 dB**
- Ratio: **2.5:1**
- Lookahead: **1 ms**
- Attack: **200 ms**
- Release: **1000 ms**

Target gain reduction: 3–6 dB on loud parts, 0–2 dB on quiet parts.

### 3. Loudness Staging — Loudness Normalization

Per-stem before final mixdown:

- Vocal stem: **−18 LUFS**
- Instrumental stem: **−21 LUFS**
- Differential: **3 dB** (vocal louder — drives cross-room intelligibility)

### 4. Final Limiter — Limiter (on combined mix)

- Threshold: **−3.0 dB**
- Make-up target: **−1.0 dB** (true peak ceiling)
- Knee width: **2.0 dB**
- Lookahead: **5 ms**
- Release: **100 ms**

### 5. Final Loudness Pass — Loudness Normalization

- Integrated target: **−14 LUFS** (streaming/TV standard: Spotify, YouTube, Apple)
- True peak: **−1 dBTP**

---

## Reference Test

Final master must be evaluated at **TV listening volume from an adjacent room** (kitchen/dining). If vocal disappears, raise vocal stem by 1 dB and re-render — do not boost limiter.

## Notes for Future Sessions

- Nasal frequency (1.2 kHz) is voice-specific — re-sweep for new singers.
- Do not stack additional limiting; final master is already at streaming-normalized loudness.
- If sibilance becomes harsh after the 3 kHz presence boost, add a de-esser between EQ and compression (step 1.5).
