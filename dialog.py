import wx
import re
import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
from utility import (
	convert_speak_parameter_to_string,
load_pickle_data,
SRAPI,
)
from pywubi import wubi
from BaseUI import (
	StatisticDialog,
	SpeedDialog,
	PreferencesDialog,
	EditDialog,
	WuBiDialog,
	HanZiDialog,
	)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WuBiSearchDialog(WuBiDialog):
	def __init__(self, *args, **kwds):
		super().__init__(*args, **kwds)

	def OnSearchBTN(self, evt):
		text = self.combo_box_input.GetValue()
		if not text: return
		self.tc_result.SetValue('')
		result = self._Search(text)
		retval = []
		for i in result:
			if isinstance(i, list):
				retval.append('\n'.join(i[::-1]) + '\n')
			else:
				retval.append(i)
		self.tc_result.SetValue('\n'.join(retval))
		self.tc_result.SetFocus()

	def OnSearchCB(self, evt):
		# text = self.combo_box_input.GetValue()
		text = evt.GetString()
		if not text: return
		self.tc_result.SetValue('')
		result = self._Search(text)
		retval = []
		for i in result:
			if isinstance(i, list):
				retval.append('\n'.join(i[::-1]) + '\n')
			else:
				retval.append(i)
		# print(retval)
		self.tc_result.SetValue('\n'.join(retval))
		self.tc_result.SetFocus()

	def _Search(self, text):
		single_char = self.choice_single.GetSelection()
		shortest = False if single_char == 1 else True
		multicode = True if single_char == 2 else False
		if len(text) ==1:
			result = wubi(text, shortest = shortest, multicode = multicode)
			return  result[::-1]
		multi_char = self.choice_multi.GetSelection()
		if multi_char == 0:
			shortest = False
			single = False
		else:
			single = True
		result = wubi(text, shortest = shortest, multicode=multicode, single = single)
		return result



class HanZiSearchDialog(HanZiDialog):
	def __init__(self, *args, **kwds):
		super().__init__(*args, **kwds)
		self.hanzi_data = None

	def _local_hanzi_data(self, text):
		if self.hanzi_data is None:
			self.hanzi_data = load_pickle_data('hanzi.data')
			if not self.hanzi_data:
				return '找不到数据库'
		result = self.hanzi_data.get(text, {})
		result_text = ''
		for k,v in result.items():
			result_text += f'{k}: {v}\n'
		return result_text

	def _hanyu_baidu(self, text):
		url = f'https://hanyu.baidu.com/s?wd={text}'
		response = requests.get(url)
		if response.status_code != 200:
			return str(response.status_code)

		soup = BeautifulSoup(response.text, 'html.parser')
		# 拼音
		pinyin = soup.find(id='pinyin')
		pinyin = pinyin.get_text(strip=True) if pinyin else ''
		# 部首
		radical = soup.find(id='radical')
		radical = radical.get_text(strip=True) if radical else ''
		# 笔画数
		stroke_count = soup.find(id='stroke_count')
		stroke_count = stroke_count.get_text(strip=True) if stroke_count else ''
		# 五行
		wuxing = soup.find(id='wuxing')
		wuxing = wuxing.get_text(strip=True) if wuxing else ''
		# 五笔
		wubi = soup.find(id='wubi')
		wubi = wubi.get_text(strip=True) if wubi else  ''
		# 基本释义
		basic_meaning = soup.find(id='basicmean-wrapper')
		if basic_meaning: basic_meaning = basic_meaning.find('p')
		basic_meaning = basic_meaning.get_text(strip=True) if basic_meaning else  ''
		# 详细释义。查找 id 为 'detailmean-wrapper' 的 div 内的所有释义段落
		detail_meaning = ''
		detail_meaning_section = soup.find(id='detailmean-wrapper')
		detail_meanings = detail_meaning_section.find_all('p') if detail_meaning_section else []
		detail_meaning_texts = [meaning.get_text(strip=True) for meaning in detail_meanings]
		# 笔顺。查找 class 为 'word-stroke-val' 的元素
		stroke_order_text  = ''
		stroke_order = soup.find_all(class_='word-stroke-val')
		stroke_order_text = [stroke.get_text(strip=True) for stroke in stroke_order]
		if pinyin or radical or stroke_count or wuxing or wubi or basic_meaning or detail_meaning or stroke_order:
			retval = f'''笔顺： {' '.join(stroke_order_text)} 
 {wubi} 
			拼音： {pinyin} 
 {radical} 
 {stroke_count} 
 {wuxing} 
			基本释义： {basic_meaning} 
			详细释义： {' '.join(detail_meaning_texts)}  
			'''
			return retval
		retval = re.sub(r'[\r\n]{2,}', '\n', soup.get_text())
		retval = re.sub(r'(^.+?百度首页)|(© Baidu.+$)', '', retval, flags = re.S)
		retval = re.sub(r'^\s+\r?\n', '', retval, flags =re.M)
		return retval

	def _hanzipi(self, text):
		url = f'https://www.hanzipi.com/{text}.html'
		headers = {
			'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36 Edg/104.0.1293.70',
			'Referer':'https://www.hanzipi.com/',
		}
		response = requests.get(url, headers=headers, verify=False)
		if response.status_code != 200:
			return f'请求失败，错误码： {response.status_code}'
		response.encoding = 'utf-8'
		soup = BeautifulSoup(response.text, 'html.parser')
		table = soup.find('table')
		result = ''
		# 遍历 table 中的每一行
		for row in table.find_all('tr'):
			# 遍历每一行中的每一单元格
			for cell in row.find_all('td'):
				# 翻译和释义单元格包含p 标签
				# ps = cell.find_all('p')
				# if ps: # and ps[0].find('span', class_='z_ts2'):
					# texts = [p.get_text() for p in ps]
					# result += '\n'.join(texts) + '\n'
					# exclude_p  = ''.join([text.strip() for text in cell.find_all(string = True,recursive = False)])
					# if exclude_p: result += f'\n{exclude_p}\n'
				# else:
					# result += f'{cell.get_text(strip=True)}\n'
				result += cell.get_text(separator='\n', strip = True) + "\n"

		return result

	def _search(self):
		text = self.combo_box_input.GetValue()
		if not text: return
		source = self.combo_box_source.GetStringSelection()
		if source == '本地':
			result_text = self._local_hanzi_data(text)
		elif source == '汉语':
			result_text = self._hanyu_baidu(text)
		elif source == '汉字':
			result_text = self._hanzipi(text)

		self.tc_result.SetValue(result_text)
		self.tc_result.SetFocus()

	def OnSearchBTN(self, evt):
		self._search()

	def OnSearchCB(self, evt):
		self._search()


class EditSchemeDialog(EditDialog):
	def __init__(self, *args,
			  title = '添加', 
			  name_content = [], 
			  old_content = [],
			  new_content=[], 
			  mode = '',
			  **kwds):
		super().__init__(*args, **kwds)
		self.mode = mode
		self.name_content = name_content
		self.SetTitle(title)
		if name_content:
			self.combo_box_name.Set(name_content)
			self.combo_box_name.SetSelection(0)
		if old_content:
			self.tc_content.SetValue('\n'.join(old_content) + '\n')
		if new_content:
			self.tc_content.AppendText('\n'.join(new_content))
		if mode == 'view':
			self.combo_box_name.SetEditable(False)
			self.tc_content.SetEditable(False)
		elif mode == 'edit':
			self.name_content = name_content[0]

	def OnAddIncorrectBTN(self, evt):
		self.scheme_name = self.combo_box_name.GetValue()
		if not self.scheme_name:
			wx.MessageBox('方案名称不能为空', '警告')
			return
		if self.mode == 'new':
			if self.scheme_name in self.Parent.scheme_keys[self.Parent.parent_text]:
				wx.MessageBox('该方案名称已存在', '警告')
				return
		elif self.mode == 'edit':
			if self.scheme_name != self.name_content and self.scheme_name  in self.Parent.scheme_keys[self.Parent.parent_text]:
				wx.MessageBox('编辑后的方案名称与其它名称重复', '警告')
				return
		self.scheme_content = self.tc_content.GetValue().split()
		evt.Skip()





class MyPreferencesDialog(PreferencesDialog):
	def __init__(self, *args,waiting_time=0,  speak_mode=0,
			  voices= [],
			  rate = 80,
			  pitch = 50,
			  volume = 80,
			**kwds):
		super().__init__(*args, **kwds)
		self.combo_box_time.Set(['不限制'] + [str(i) for i in range(1, 61)])
		self.combo_box_time.SetSelection(waiting_time)
		self.choice_speak_mode.SetSelection(speak_mode)
		self.SetVoiceCtrl(speak_mode == 1)
		self.choice_voice.Set(voices)
		self.choice_voice.SetStringSelection(self.Parent.voice)
		self.slider_rate.SetValue(rate)
		self.slider_pitch.SetValue(pitch)
		self.slider_volume.SetValue(volume)

	def OnListen(self, evt):
		text = '你好，你们的你，好坏的好'
		string = self.choice_speak_mode.GetStringSelection()
		if string == '读屏':
			self.Parent._SpeakWithLiveRegion(text)
		elif string == '内置语音库':
			self.Parent._SpeakWithNeural(text,
			voice = self.choice_voice.GetStringSelection(),
			rate = convert_speak_parameter_to_string((self.slider_rate.GetValue() - 50)*4),
			pitch = convert_speak_parameter_to_string(self.slider_pitch.GetValue() - 50),
			volume = convert_speak_parameter_to_string(self.slider_volume.GetValue() - 80)
		)
		elif string == '争渡API':
			self.api = SRAPI('ZDSRAPI.dll', error_msg=True)
			if self.api is not None:
				self.api.speak(text)
		elif string == 'NVDA API':
			self.api = SRAPI('nvdaControllerClient.dll', error_msg = True)
			if self.api is not None:
				self.api.speak(text)

	def OnSpeakMode(self, evt):
		string = evt.GetString()
		flag = string == '内置语音库'
		self.SetVoiceCtrl(flag)

	def SetVoiceCtrl(self, flag):
		self.choice_voice.Enable(flag)
		self.slider_volume.Enable(flag)
		self.slider_rate.Enable(flag)
		self.slider_pitch.Enable(flag)
		# self.btn_listen_.Enable(flag)


class MeasureSpeedDialog(SpeedDialog):
	def __init__(self, *args, **kwds):
		super().__init__(*args, **kwds)
		self.processing = False
		self.tc_typing.Bind(wx.EVT_TEXT_PASTE, self.OnPaste)

	def OnPaste(self, evt):
		return

	def OnStart(self, evt):
		if self.processing:
			time_span = (datetime.now() - self.starts_time).seconds
			self.processing = False
			self.btn_start.SetLabel('开始(&S)')
			text = self.tc_typing.GetValue()
			text = re.sub(r'[^\u4e00-\u9fff]+', '', text)
			report = '\n'.join(((f'共输入 {len(text)} 字。',
				f'用时 {time_span} 秒。',
				f'平均打字速度： {round(len(text) / (time_span / 60), 0)} 字/分钟',
			)))
			dlg = StatisticDialog(self)
			dlg.button_OK.Disable()
			dlg.button_OK.Hide()
			dlg.tc_display.SetValue(report)
			if dlg.ShowModal() == wx.ID_OK:
				pass
			dlg.Destroy()
			return

		self.tc_typing.SetValue('')
		self.tc_typing.SetFocus()
		self.processing = True
		self.btn_start.SetLabel('结束 (&S)')
		self.starts_time = datetime.now()


	def OnClose(self, evt):
		self.Destroy()


class TypingStatisticDialog(StatisticDialog):
	def __init__(self, *args, **kwds):
		super().__init__(*args, **kwds)
		self.button_OK.SetLabel('将错误字词添加到练习方案')
		self.button_CANCEL.SetLabel('取消')


if __name__ == "__main__":
	app = wx.App(False)  # 创建一个wx.App实例
	# dlg = TypingStatisticDialog(None)
	# dlg = MyPreferencesDialog(None)
	# dlg = WuBiSearchDialog(None)
	dlg = HanZiSearchDialog(None)
	dlg.ShowModal()
	dlg.Destroy()  
	app.MainLoop()  # 启动主事件循环
