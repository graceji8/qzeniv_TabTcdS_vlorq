from omnivoice import OmniVoice
import soundfile as sf
import torch

model = OmniVoice.from_pretrained("k2-fsa/OmniVoice")  # CPU, no GPU needed

# Chinese
audio = model.generate(text="水墨画是中国传统绘画艺术，以墨为主要颜料。")
sf.write("chinese.wav", audio[0], 24000)

# Japanese
audio = model.generate(text="浮世絵は江戸時代に花開いた日本の伝統絵画です。")
sf.write("japanese.wav", audio[0], 24000)

# Arabic
audio = model.generate(text="الفن الإسلامي هو تعبير عن الجمال والروحانية.")
sf.write("arabic.wav", audio[0], 24000)