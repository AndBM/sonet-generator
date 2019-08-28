import os

import config
import markovify
import pronouncing

# Make it object oriented!!!

# 1) Generate Markov model
# 2) Generate a short sentence
# 3) Check the number of syllables, if incorrect go to 2)
# 4) Repeat 1-3 until a rhyming sentence is found
# 5) Write out ABAB verse


class ABAB_poem:
    def __init__(self):
        self.config = config.Config()

    def generate_poem(self):

        all_text = ""
        for i in os.listdir(self.config.markovify_input_dir):
            with open(self.config.markovify_input_dir + i) as f:
                all_text += f.read()
        text_model = markovify.Text(all_text)

        poemNotDone = 1

        while poemNotDone:
            print("looking for first...")
            first = None
            phones = []
            while (
                first == None
                or sum([pronouncing.syllable_count(p) for p in phones])
                != self.config.poem_first_syl_count
            ):
                first = text_model.make_short_sentence(
                    self.config.poem_first_syl_count
                    * self.config.poem_avg_char_per_syl,
                    tries=100,
                    max_overlap_ratio=self.config.markovify_max_overlap_ratio,
                    max_overlap_total=self.config.markovify_max_overlap_total,
                )
                if first == None:
                    continue

                firstNoPunctuation = first[0:-1]
                try:
                    phones = [
                        pronouncing.phones_for_word(p)[0]
                        for p in firstNoPunctuation.split()
                    ]
                except IndexError:
                    # Word not found in dictionary
                    phones = []

            # print("looking for second...")
            # second = None
            # phones = []
            # while second == None or sum([pronouncing.syllable_count(p) for p in phones]) != self.config.poem_second_syl_count:
            #     second = text_model.make_short_sentence(
            #         self.config.poem_second_syl_count * self.config.poem_avg_char_per_syl,
            #         tries=100,
            #         max_overlap_ratio=self.config.markovify_max_overlap_ratio,
            #         max_overlap_total=self.config.markovify_max_overlap_total
            #     )
            #     secondNoPunctuation = second[0:-1]
            #     try:
            #         phones = [pronouncing.phones_for_word(p)[0] for p in secondNoPunctuation.split()]
            #     except IndexError:
            #         # Word not found in dictionary
            #         phones = []
            second = "Not too bad"

            # Try to generate rhyming lines
            print("looking for third...")
            third = None
            phones = []
            rhymeAttempts = 0
            while (
                third == None
                or sum([pronouncing.syllable_count(p) for p in phones])
                != self.config.poem_first_syl_count
                or thirdNoPunctuation[-1]
                not in pronouncing.rhymes(firstNoPunctuation[-1])
            ) and rhymeAttempts < self.config.max_rhyme_attempts:
                third = text_model.make_short_sentence(
                    self.config.poem_first_syl_count
                    * self.config.poem_avg_char_per_syl,
                    tries=100,
                    max_overlap_ratio=self.config.markovify_max_overlap_ratio,
                    max_overlap_total=self.config.markovify_max_overlap_total,
                )
                if third == None:
                    continue

                thirdNoPunctuation = third[0:-1]
                try:
                    phones = [
                        pronouncing.phones_for_word(p)[0]
                        for p in thirdNoPunctuation.split()
                    ]
                except IndexError:
                    # Word not found in dictionary
                    phones = []
                    continue
                # If this fails, it must be the rhyme.
                rhymeAttempts += 1
                # print(rhymeAttempts)

            # Check if we actually made a rhyme
            if rhymeAttempts < self.config.max_rhyme_attempts:
                print("Done")
                poemNotDone = 0  # Poem done

        fourth = second

        poem = "".join([first, "\n", second, "\n", third, "\n", fourth])
        # poem = "".join(c for c in poem if c not in ('!','.',':','?',';')) #Remove punctuation, I guess?

        print("")
        print("***********************")
        print("-----------------------")
        print(poem)
        print("-----------------------")
        print("***********************")

        return poem


# Generate the poem
ABAB_poem().generate_poem()
