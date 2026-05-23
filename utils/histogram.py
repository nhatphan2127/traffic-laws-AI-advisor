import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
def visualize_chunk_distribution(chunks):
    """
    Calculates the length of each chunk and plots the frequency distribution.
    """
    if not chunks:
        print("No chunks to visualize.")
        return

    # 1. Extract lengths (Character count and Word count)
    char_lengths = [len(c['text']) for c in chunks]
    word_lengths = [len(c['text'].split()) for c in chunks]

    # Create a DataFrame for easier plotting
    df = pd.DataFrame({
        'Characters': char_lengths,
        'Words': word_lengths
    })

    # 2. Setup Plotly/Seaborn Style
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # Plot 1: Character Length Distribution
    sns.histplot(df['Characters'], bins=30, kde=True, ax=axes[0], color='skyblue')
    axes[0].set_title('Distribution of Character Lengths')
    axes[0].set_xlabel('Number of Characters')
    axes[0].set_ylabel('Frequency')

    # Plot 2: Word Length Distribution
    sns.histplot(df['Words'], bins=30, kde=True, ax=axes[1], color='salmon')
    axes[1].set_title('Distribution of Word Lengths')
    axes[1].set_xlabel('Number of Words')
    axes[1].set_ylabel('Frequency')

    # 3. Add statistical summary as text
    stats_text = (
        f"Total Chunks: {len(chunks)}\n"
        f"Avg Chars: {df['Characters'].mean():.1f}\n"
        f"Max Chars: {df['Characters'].max()}\n"
        f"Min Chars: {df['Characters'].min()}\n"
        f"Median Chars: {df['Characters'].median()}"
    )
    plt.figtext(0.5, -0.05, stats_text, ha="center", fontsize=12, 
                bbox={"facecolor":"orange", "alpha":0.2, "pad":5})

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.3)
    plt.savefig(Path('statistic_img/chunk.jpg'))
    plt.show()
