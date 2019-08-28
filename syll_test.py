import os

import config
import markovify

config = config.Config()

all_text = ""
for file in os.listdir(config.markovify_input_dir):
    with open(config.markovify_input_dir + file) as f:
        all_text += f.read()
text_model = markovify.Text(all_text)

line = text_model.make_short_sentence(
    config.poem_first_syl_count * config.poem_avg_char_per_syl,
    tries=100,
    max_overlap_ratio=config.markovify_max_overlap_ratio,
    max_overlap_total=config.markovify_max_overlap_total,
)

print(line)
