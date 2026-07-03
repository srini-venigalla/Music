import pygame
import time
import sys

def play_coffee_beat(bpm=128, repetitions=16):
    """
    Synthesizes the 'Coffee Coffee' staccato rhythm.
    BPM: Heartbeat of the programmer.
    """
    pygame.mixer.init()
    
    # In a real architectural build, you'd load a dry 'Coffee' sample.
    # For this script, we assume 'coffee.wav' exists in your root.
    try:
        sample = pygame.mixer.Sound("coffee.wav")
    except FileNotFoundError:
        print("Error: 'coffee.wav' not found. Please provide a dry vocal sample.")
        return

    # Calculate the 'Ratchet' interval (1/8th notes for that TikTok feel)
    # 60 seconds / BPM / 2 (for the 'Coffee Coffee' double-tap)
    interval = (60 / bpm) / 2 

    print(f"--- Starting Caffeine Loop: {bpm} BPM ---")
    
    try:
        for i in range(repetitions):
            # The 'Coffee' trigger
            sample.play()
            
            # The 'Logic Gate': 
            # High-precision sleep to maintain the 'Music Music' cadence
            time.sleep(interval)
            
            # Print to console to visualize the 'Coffee' pulse
            sys.stdout.write("Coffee... ")
            sys.stdout.flush()
            
            if (i + 1) % 4 == 0:
                print(" [STACCATO]")
                
    except KeyboardInterrupt:
        print("\nLoop terminated by User. System cooling down.")
    finally:
        pygame.mixer.quit()

# Execute the loop
if __name__ == "__main__":
    # 128 BPM is the standard 'House' and 'TikTok' tempo
    play_coffee_beat(bpm=128, repetitions=32)