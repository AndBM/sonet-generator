import pronouncing as pnc
import os
import markovify
import config
import string
import syllabifyARPA as ARPA
import re


class Poem:
    """An auto-generated poem with lines based on the text corpus stated in the
    config file. A rhyme pattern argument can be passed for the constructor."""

    def __init__(self, pattern='A7A7B7B7'):
        self.config = config.Config()

        all_text = ''
        for file in os.listdir(self.config.markovify_input_dir):
            with open(self.config.markovify_input_dir + file) as f:
                all_text += f.read()
        self.text_model = markovify.Text(all_text)

        self.poem = self.generate_poem(pattern)

    def generate_poem(self, pattern):
        """Generate a poem with a rhyme and syllable pattern as followed in the argument,
        e.g 'ABAB5757'. Upper and lower case letters are differentiated. For lines
        which should not necessarily rhyme, '0' should be passed, e.g. 'AA0BB55755'
        where there third line will not be part of a rhyme pattern."""

        # Ensure even number of input
        assert len(pattern) % 2 == 0, "Number of input characters must be even!"
        line_num = int(len(pattern)/2)
        print(range(line_num))

        # Set up basic objects of the poem. Syntax:
        # Line ( line number, rhyme group, syllables, sentence )
        lines = [{'index': i, 'rhyme': pattern[i], 'syls': pattern[line_num+i], 'sent': None}
                 for i in range(line_num)]
        line_pairings = {c: [] for c in pattern[0:line_num-1] if not c == '0'}
        for rhyme in line_pairings:
            line_pairings[rhyme] = [l for l in lines if l['rhyme'] == rhyme]
        non_rhymes = [l for l in lines if l['rhyme'] == '0']
        final_lines = []

        print(lines)
        print(line_pairings)

        # Find rhymes for each group. Rhyme is letter (A), group is the object
        for rhyme, group in zip(line_pairings, line_pairings.values()):
            print('Looking for rhymes for ' + rhyme + ' group.')
            # Create first sentence in the group
            group[0]['sent'] = self._new_sentence(group[0]['syls'])
            current = 1

            # Prepare iteration to find rhymes
            n_lines = len(group)
            rhyme_attempts = 0
            max_tries_per_sent = 30
            n = 0 # Just for animation

            # INFINITE LOOP WOOO LET'S GO
            while True:
                if current == n_lines:
                    # If we have all the rhymes needed, pack into poem and move on to the next rhyme group
                    final_lines += group
                    break

                if rhyme_attempts % 50 == 0:
                    # Fancy animation
                    n += 1
                    #print('\r' + n * '.', end='')
                if n == 20:
                    n = 0

                rhyme_attempts += 1
                if rhyme_attempts > max_tries_per_sent:
                    # Restart from first sentence in group
                    group[0]['sent'] = self._new_sentence(group[0]['syls'])
                    current = 1

                # Generate next line
                group[current]['sent'] = self._new_sentence(group[0]['syls'])

                # Flexibly check if the line rhymes
                if is_rhyme_pair(group[0]['sent'], group[current]['sent']):
                    # Rhyme found! Ensure that it is different from other groups
                    already_used = False
                    for prev_sent in final_lines:
                        if is_rhyme_pair(prev_sent['sent'], group[current]['sent']):
                            already_used = True
                            print("Rhyme already used, trying something else.")
                    if not already_used:
                        rhyme_attempts = 0
                        current += 1

            print()

        # Put whatever on the non-rhyming line
        for line in non_rhymes:
            line['sent'] = self._new_sentence(group[0]['syls'])

        # Sort the rhymes into the desired structure
        final_lines += non_rhymes
        final_lines.sort(key=lambda x: x['index'])

        return '\n'.join(line['sent'] for line in final_lines)

    def print_poem(self):

        length = max(len(line) for line in self.poem.split('\n'))

        print('*' * length)
        print('-' * length)
        print(self.poem)
        print('-' * length)
        print('*' * length)

    def _new_sentence2(self,syls):
        syls = int(syls)
        sent = None
        phones = []
        while sent == None or sum([pnc.syllable_count(p) for p in phones]) != syls:
            print(sent)
            print(sum([pnc.syllable_count(p) for p in phones])-syls)
            sent = self.text_model.make_short_sentence(
                syls * self.config.poem_avg_char_per_syl,
                tries=100,
                max_overlap_ratio=self.config.markovify_max_overlap_ratio,
                max_overlap_total=self.config.markovify_max_overlap_total
            )
            if sent == None:
                continue

            sentNoPunctuation = sent[0:-1]
            try:
                phones = [pnc.phones_for_word(p)[0] for p in sentNoPunctuation.split()]
            except IndexError:
                # Word not found in dictionary
                phones = []

        return ''.join(c for c in sent if c not in string.punctuation)

    def _new_sentence(self,syls):
        #TODO Make markovify actually make the right number of syllables
        # Implement syllable tester from ababGenerator
        syls = int(syls)
        sent = self.text_model.make_short_sentence(
            syls * self.config.poem_avg_char_per_syl,
            tries=100,
            max_overlap_ratio=self.config.markovify_max_overlap_ratio,
            max_overlap_total=self.config.markovify_max_overlap_total
        )

        if sent == None:
            return None
            
        # Might be double work checking for punctuation
        sentNoPunctuation = sent[0:-1]
        try:
            phones = [pnc.phones_for_word(p)[0] for p in sentNoPunctuation.split()]
        except IndexError:
            # Word not found in dictionary
            phones = []

        if sum([pnc.syllable_count(p) for p in phones]) != syls or not sent:
            return None
        else:
            return ''.join(c for c in sent if c not in string.punctuation)


def rhyme_degree(target_word, test_word):
    """Returns a number between 0 and 1 as the degree of rhyming between two
    words, with 1 being an exact rhyme and 0 being no similarity at all."""

    if test_word in pnc.rhymes(target_word):
        print('\rFound rhyme pair from the pronouncing library:')
        print(target_word, 'and', test_word)
        return 1

    # extract word part from last stressed syllable excluding that syll's onset
    rhymes = {target_word: None, test_word: None}
    for word in rhymes:
        try:
            pron = pnc.phones_for_word(word)[0]
        except IndexError:  # in case one of the words is not in the dictionary
            return 0
        # get stress pattern and find last stressed syllables
        stress = pnc.stresses(pron)
        last_stress = max([stress.rfind('1'), stress.rfind('2')])
        try:
            sylls = ARPA.syllabifyARPA(pron, return_list=True)
        except ValueError:  # in case the word cannot be syllabified
            return 0
        sylls = sylls[last_stress:]
        first_onset = re.split(ARPA.VOWELS_REGEX, sylls[0])[0]
        sylls[0] = sylls[0].replace(first_onset, '', 1)
        rhymes[word] = sylls

    # test for matching vowels and consonant clusters in onset and coda
    # the stressed vowel weighs double
    phones = 1 + max([sum(len(syll.split()) for syll in rhyme)
                      for rhyme in rhymes.values()])
    matches = 0
    for target_syll, test_syll in zip(rhymes[target_word], rhymes[test_word]):
        target_vowel = [phone for phone in target_syll.split()
                        if re.match(ARPA.VOWELS_REGEX, phone)][0]
        test_vowel = [phone for phone in test_syll.split()
                      if re.match(ARPA.VOWELS_REGEX, phone)][0]
        target_clusters = target_syll.split(target_vowel)
        test_clusters = test_syll.split(test_vowel)
        # measure match of syllable onsets
        matches += len(
            set(target_clusters[0].strip().split()).intersection(
                set(test_clusters[0].strip().split())
            )
        )
        # measure match of vowels
        if target_vowel[:2] == test_vowel[:2]:  # test for the vowel itself
            matches += 1
            if (target_vowel[-1] in ['1', '2'] and
                target_vowel[-1] == test_vowel[-1]):  # test for similar stress
                matches += 1
        # measure match of syllable codas
        matches += len(
            set(target_clusters[1].strip().split()).intersection(
                set(test_clusters[1].strip().split())
            )
        )
    degree = matches / phones
    if degree > 0.7:
        print('\rFound rhyme pair with a rhyming degree of: ', degree)
        print(rhymes)
    return degree


def is_rhyme_pair(target_line, test_line, same_allowed=False, min_degree=0.8):
    """Return true if the passed lines rhyme."""

    if not target_line or target_line == '' or not test_line or test_line == '':
        return False

    target_last = target_line.split()[-1]
    test_last = test_line.split()[-1]

    if target_last.lower() == test_last.lower() and not same_allowed:
        return False

    # TODO: take into account short words
    degree = rhyme_degree(target_last, test_last)
    if degree > min_degree:
        return True
    else:
        return False


poem = Poem('ABAB5757')
poem.print_poem()
