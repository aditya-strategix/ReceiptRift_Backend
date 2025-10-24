import pytesseract
from PIL import Image
import os,argparse
import cv2
import re
import numpy as np
#Tesseract path

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
image_want_from_text=[]
def ocr_parser(image):
   # # arg parse 
   # ap=argparse.ArgumentParser()
   # ap.add_argument("-i","--image",required=True,help="Path to input image")
   # ap.add_argument("-p","--pre_processor",default="thresh",help="the preprocessor usage")
   # args=vars(ap.parse_args())
   data = pytesseract.image_to_string(image)
   print(data)

   # # read and preprocess image
   # images=cv2.imread(args["image"])
   gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)

   # if args["pre_processor"]=="blur":
   #    gray=cv2.medianBlur(gray,3)
   # if args["pre_processor"]=="thresh":
   #    gray=cv2.threshold(gray,0,255,cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

   # ocr with coordinates
   data=pytesseract.image_to_data(gray,output_type=pytesseract.Output.DICT)
   # print(data)
   n_boxes=len(data["text"])
   line_dict={}

   #group words by y axis using pytesseract
   for i in range(n_boxes):
      if int(data["conf"][i])>30:
         line_num=data['line_num'][i]
         if line_num not in line_dict:
            line_dict[line_num]=[]
         line_dict[line_num].append({
         'text':data["text"][i],
         'left':data["left"][i]
         })

   #sort words in each line by x coordinates
   lines=[]
   for i in sorted(line_dict.keys()):
      words=sorted(line_dict[i],key=lambda w:w['left'])
      line_text=" ".join(w['text'] for w in words)
      lines.append(line_text)

   items=[]

   # more robust parsing: last numeric token => total price; previous integer token (if any) => quantity
   for line in lines:
      line = line.strip()
      if not line:
         continue

      # normalize commas in numbers
      norm = line.replace(',', '')
      # find all numeric tokens like 330, 330.00
      nums = re.findall(r'\d+(?:\.\d+)?', norm)
      if not nums:
         continue

      # last numeric token is treated as total price
      try:
         total_str = nums[-1]
         total_price = float(total_str)
      except Exception:
         # cannot parse price
         continue

      quantity = 1
      # if there's a preceding numeric token that is an integer and reasonable, treat as quantity
      if len(nums) >= 2:
         prev = nums[-2]
         if '.' not in prev:
            try:
               q = int(prev)
               if 1 <= q <= 100:  # heuristic limit
                  quantity = q
            except Exception:
               pass

      # attempt to remove the numeric tokens (price and maybe quantity) from the end of the line to get the name
      tokens = line.split()
      # remove tokens from the end that correspond to price/quantity numeric strings (compare after removing commas)
      removed = 0
      to_remove = {str(nums[-1])}
      if quantity != 1 and len(nums) >= 2:
         to_remove.add(str(nums[-2]))

      # handle tokens that may contain numeric + suffix (e.g. "360.00" or "360.00/") by matching numeric substring
      filtered = []
      # iterate tokens left-to-right and skip the last N numeric tokens from the end
      # easier: iterate tokens reversed and skip when they match a numeric pattern and still in to_remove
      temp = []
      skip_count = 0
      i = len(tokens) - 1
      while i >= 0:
         t = tokens[i]
         t_norm = t.replace(',', '')
         if skip_count < len(to_remove) and re.fullmatch(r'\d+(?:\.\d+)?', t_norm):
            skip_count += 1
            i -= 1
            continue
         temp.append(tokens[i])
         i -= 1
      # rebuild name from remaining tokens (reverse temp)
      name = ' '.join(reversed(temp)).strip()
      # final cleanup
      name = re.sub(r'[\-–—]{2,}', '-', name)
      name = name.strip()
      if not name:
         # fallback: take whole line excluding last numeric sequence
         name = re.sub(re.escape(nums[-1]) + r'\s*$', '', norm).strip()

      unit_price = round(total_price / quantity, 2) if quantity else total_price
      if unit_price <= 0 or total_price <= 0 or not name:
         continue
      if unit_price > total_price:
         continue
      if unit_price > 10000:
         continue
      items.append({
         "name": name,
         "quantity": quantity,
         "total_price": total_price,
         "unit_price": unit_price
      })
      # debug log for each parsed line
      print(f"[ocr_parser] parsed line -> name: '{name}', qty: {quantity}, total: {total_price}, unit: {unit_price}")

   #Output
   return items
