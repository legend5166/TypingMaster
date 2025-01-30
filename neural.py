import os
import azure.cognitiveservices.speech as sdk
from azure.cognitiveservices.speech.audio import *
from azure.cognitiveservices.speech.enums import *

class NeuralSynthesizer:
	def __init__(self, 
		voice = "Microsoft Xiaoxiao (Natural) - Chinese (Simplified, China)",
		):
		self.sc = sdk.EmbeddedSpeechConfig()
		self.sc.disable_telemetry()
		self.sc.set_property_by_name("EmbeddedSpeech-DisableTelemetry", "true")
		voicepath = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'voices')
		for f in os.listdir(voicepath):
			self.sc.add_path(os.path.join(voicepath, f))
		self.sc.set_tts_key("ZCjZ7nHDSLvf4gpELteM4AnzaWUjTpn7UkV7D@vvksl0w1SNgon6d1905WANbktDc9S39oaA4r29HJNayXvTq8fJsq")
		self.sc.set_tts_voice(voice)
		# self.sc.set_tts_voice("Microsoft Xiaoxiao (Natural) - Chinese (Simplified, China)")
		self.sc.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat(16))
		#SpeechSynthesisOutputFormat(16) 是一个枚举值， 表示 24000hz, 16 bit, mono, PCM 
		# ac 智能传一个参数，stream 表示输出音频流， 可从回调获取数据保存为文件。 
		self.ac = sdk.audio.AudioOutputConfig(use_default_speaker=True)
		self.synth = sdk.SpeechSynthesizer(self.sc, self.ac)
		# synth = sdk.SpeechSynthesizer(speech_config=sc) # 不传audio_connfig 参数默认输出雨音
		self.is_speaking = False
		self.voices = []
		for v in self.synth.get_voices_async().get().voices:
			self.voices.append(v.name)
			# self.voices.append({"name": v.name, "locale": v.locale, "short": v.short_name})
		self.synth.synthesis_started.connect(self.synthesis_started)
		self.synth.synthesis_canceled.connect(self.synthesis_canceled)
		self.synth.synthesis_completed.connect(self.synthesis_completed)
		self.synth.bookmark_reached.connect(self.bookmark_reached)

	def synthesis_started(self,ev):
		pass

	def synthesis_canceled(self, ev):
		pass

	def bookmark_reached(self, event):
		pass

	def synthesis_completed(self, ev):
		self.is_speaking = False

	def get_voices(self):
		return self.voices

	def stop(self):
		self.synth.stop_speaking_async().get()
		self.is_speaking = False

	def generate_ssml(self,
			text,
			voice="Microsoft Xiaoxiao (Natural) - Chinese (Simplified, China)",
			rate="+60%",
			pitch="+0%",
			volume="+0%"
			):
		ssml_template = f"""
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang='zh-CN'>
<voice name="{voice}">
	<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">
{text}
</prosody>
</voice>
</speak>
"""
		return ssml_template.strip()

	def speak(self,
			text,
			voice="Microsoft Xiaoxiao (Natural) - Chinese (Simplified, China)",
			rate="+60%",
			pitch="+0%",
			volume="+0%"
			):
		ssml = self.generate_ssml(text,voice=voice, rate=rate, pitch=pitch, volume = volume)
		self.synth.speak_ssml_async(ssml)
		self.is_speaking = True

if __name__ == '__main__':
	synth = NeuralSynthesizer()
	text = ' '
	while  text:
		text = input("请输入要合成的文本：")
		synth.speak(text)


