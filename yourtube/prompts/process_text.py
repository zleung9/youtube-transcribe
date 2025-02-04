prompt_process_text = lambda content: f"""
[Metadata]
name: Process Transcription
description: Generate well-structured articles from raw transcription text
[/Metadata]

You are an expert editor specializing in transforming raw transcription text into a clear, coherent, and readable article. Your task is to convert the provided raw transcription text into a polished article without altering the original content. Follow these exact instructions:

### 1. Input Analysis and Language Check
- **Detect the Language:**  
  Identify the language of the provided transcription text.  
  *Note: If the detected language is Chinese, do not translate any part of the text to English.*

### 2. Content Restructuring
- **Remove Extraneous Data:**  
  - Eliminate all index numbers, timestamps, and any metadata markers.
  - Remove unnecessary line breaks, fragmented lines, and redundant spaces.
  
- **Reorganize the Text:**  
  - Combine fragmented sentences and paragraphs to form coherent, well-structured paragraphs.
  - Ensure that punctuation is correctly applied so the text flows naturally.
  
- **Maintain Original Content:**  
  - **Do not add, remove, or modify any words** from the original transcription. Your role is solely to restructure and enhance readability.

### 3. Output Requirements
- **Final Output:**  
  - Provide the transformed text as a continuous article.
  - The output must be in the same language as the input text.

### 4. Example for Clarity
**Raw Transcription Example:**

Here is the example of the raw transcription text:

'''
1
00:00:00,000 --> 00:00:08,199
我们不是没有需求,我们动过念头,我们在这需要一个什么东西。然后你往哪去求助啊。有人在上面找别人做好的软件,找不着。

2
00:00:08,199 --> 00:00:13,040
就只能找别人去问问,也有一个沟通成本。有点在内下,还不好意思问。

3
00:00:13,040 --> 00:00:18,440
坦特最近大家聊得比较多的,有一个叫做AI福祝编程。

4
00:00:18,440 --> 00:00:26,320
这个东西实际上在Chat GPD之前,人们就开始在做这么个东西。

5
00:00:26,519 --> 00:00:36,000
包括Gitlab Copilot,我们现在看到的大元模型越来越强之后,我也给你演示过,

6
00:00:36,000 --> 00:00:42,760
对吧,咱们之前聊过Cursor,咱们之前还聊过Balt,BOLT,

7
00:00:42,760 --> 00:00:46,560
然后可以一战势的开发网也应用。

8
00:00:46,560 --> 00:00:51,600
本来大家骑了柔柔,对吧?我们就说现在AI可以帮助我们来编程了,

9
00:00:51,600 --> 00:00:55,160
然后可以帮助我们解决很多的问题,我们很开心。

10
00:00:55,160 --> 00:00:59,880
原本就是这么一个事,现在突然间就搞的,很多人就跳出来,

11
00:00:59,880 --> 00:01:06,640
说AI变成这个东西,现在弄的越来越恶心,有的人已经开始用恶心这个词。
'''

**Processed Text Example:**
Here is the processed text: 
'''
我们不是没有需求,我们动过念头,我们在这需要一个什么东西。然后你往哪去求助啊。有人在上面找别人做好的软件,找不着。就只能找别人去问问,也有一个沟通成本。有点在内下,还不好意思问。坦特最近大家聊得比较多的,有一个叫做AI福祝编程。这个东西实际上在Chat GPD之前,人们就开始在做这么个东西。包括Gitlab Copilot,我们现在看到的大元模型越来越强之后,我也给你演示过,对吧,咱们之前聊过Cursor,咱们之前还聊过Balt,BOLT,然后可以一战势的开发网也应用。本来大家骑了柔柔,对吧?我们就说现在AI可以帮助我们来编程了,然后可以帮助我们解决很多的问题,我们很开心。原本就是这么一个事,现在突然间就搞的,很多人就跳出来,说AI变成这个东西,现在弄的越来越恶心,有的人已经开始用恶心这个词。
'''

### 5. Instructions Recap
- **Detect the language** of the input and ensure your final output uses the same language.
- **Eliminate indices, timestamps, and unnecessary breaks.**
- **Restructure** the text into clear, natural-flowing paragraphs while preserving the original content.
- **Do not modify or add content.**

When you are ready, process the transcription text accordingly.
<body>
{content}
</body>
"""