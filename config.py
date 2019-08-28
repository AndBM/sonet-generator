import os

class Config:
    def __init__(self):

        # Markovify
        self.markovify_input_dir = "./texts/"
        self.markovify_max_overlap_total = 25
        self.markovify_max_overlap_ratio = 0.8

        # Poem
        self.poem_avg_char_per_syl = 6 #pronouncing can calculate this accurately for each text
        self.poem_first_syl_count = 6
        self.poem_second_syl_count = 7

        self.max_rhyme_attempts = 30
        self.is_test = True
