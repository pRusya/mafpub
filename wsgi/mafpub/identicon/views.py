from django.shortcuts import render
from django.views import generic
from django.http import HttpResponse
from PIL import Image, ImageDraw
from hashlib import md5
import random
from PIL.ImageColor import colormap
import operator

# Create your views here.

GRID_SIZE = 9
SQUARE_SIZE = 10


class Identicon(object):
    def __init__(self, str_, background='#e6e6e6'):
        w = h = GRID_SIZE * SQUARE_SIZE
        self.image = Image.new('RGB', (w, h), background)
        self.draw = ImageDraw.Draw(self.image)
        self.hash = int(md5(str_.encode('UTF-8')).hexdigest(), 16)

        """
        sort = sorted(colormap.items(), key=operator.itemgetter(1))
        print('     SORT', sort)
        map = Image.new('RGB', (500, 200*len(colormap)), background)
        dr = ImageDraw.Draw(map)
        off = 0
        for color in sort:
            print(color[0])
            dr.rectangle((0, off, 500, off+200), color[0])
            off += 200
        map.show()"""
        #traceback.print_stack()
        #self.rand()
        #self.line()
        #self.grid(3, 2)
        #self.blocks(6, 6)
        #self.image.show()

    def rand(self):
        for i in range(5):
            x0 = random.randint(0, self.image.size[0])
            y0 = random.randint(0, self.image.size[1])
            x1 = random.randint(0, self.image.size[0])
            y1 = random.randint(0, self.image.size[1])
            self.draw.rectangle((x0, y0, x1, y1), random.choice(list(colormap.keys())))

    def line(self):
        x0 = round(self.image.size[0] / 2)
        y0 = 0
        x1 = round(self.image.size[0] / 2)
        y1 = self.image.size[1]
        self.draw.line((x0, y0, x1, y1), fill='black', width=5)
        #self.draw.point((5,5), fill='black')

    def blocks(self, x, y, n=None):
        side_width = self.image.size[0] // x
        side_height = self.image.size[1] // y

        blocks = []
        for b in range(0, y):
            for a in range(0, x):
                blocks.append((a*side_width, b*side_height, (a+1)*side_width, (b+1)*side_height))
        #print('     BLOCKS', blocks)

        if n is None:
            n = random.randint(1, round((x*y)/2))  # round((x*y)/2)
        color = random.choice(list(colormap.keys()))
        back = random.choice(list(colormap.keys()))
        w, h = self.image.size[0]//3, self.image.size[1]//3
        img_a = Image.new('RGB', (w, h), back)
        img_a.draw = ImageDraw.Draw(img_a)
        img_b = Image.new('RGB', (w, h), back)
        img_b.draw = ImageDraw.Draw(img_b)
        img_c = Image.new('RGB', (w, h), back)
        img_c.draw = ImageDraw.Draw(img_c)
        blocks_s = []
        for b in range(0, y):
            for a in range(0, x):
                blocks_s.append((a*(w//3), b*(h//3), (a+1)*(w//3)-1, (b+1)*(h//3)-1))
        #print('     BLOCKS S', blocks_s)
        for x in range(0, n):
            img_a.draw.rectangle(blocks_s[random.randint(0, len(blocks_s)-1)], color)
            img_b.draw.rectangle(blocks_s[random.randint(0, len(blocks_s)-1)], color)
            r = random.randint(0, len(blocks_s)-1)
            #print(blocks_s[r])
            img_c.draw.rectangle(blocks_s[r], color)

        off_a_1 = (0, 0)
        off_a_2 = (0, h*2)
        off_a_3 = (w*2, h*2)
        off_a_4 = (w*2, 0)

        self.image.paste(img_a, off_a_1)
        self.image.paste(img_a.rotate(90), off_a_2)
        self.image.paste(img_a.rotate(180), off_a_3)
        self.image.paste(img_a.rotate(270), off_a_4)


        off_b_1 = (w, 0)
        off_b_2 = (0, h)
        off_b_3 = (w, h*2)
        off_b_4 = (w*2, h)

        self.image.paste(img_b, off_b_1)
        self.image.paste(img_b.rotate(90), off_b_2)
        self.image.paste(img_b.rotate(180), off_b_3)
        self.image.paste(img_b.rotate(270), off_b_4)


        off_c_1 = (w, h)
        self.image.paste(img_c, off_c_1)
        #self.image.paste(img_c.rotate(90), off_c_1)
        #self.image.paste(img_c.rotate(180), off_c_1)
        #self.image.paste(img_c.rotate(270), off_c_1)
        #print(blocks)
        #for xy in blocks:
        #    self.draw.rectangle(xy, random.choice(list(colormap.keys())))
        #self.image.show()
        return

    def grid(self, x_points=3, y_points=2):
        side_width = round(self.image.size[0] / (x_points + 1))
        side_height = round(self.image.size[1] / (y_points + 1))
        points = []
        deriv_x = round(self.image.size[0] * 0.04)
        deriv_y = round(self.image.size[1] * 0.04)

        for x in range(0, x_points+2):
            points.append((x*side_width, 0))
            for y in range(1, y_points+2):
                points.append((x*side_width, y*side_height))
                #points.append((x*side_width+random.randint(-deriv_x, deriv_x), y*side_height+random.randint(-deriv_y, deriv_y)))
            #points.append((x*side_width, self.image.size[1]))
        print(points)
        for xy in points:
            self.draw.point(xy, fill='black')
        for start in range(0, len(points), x_points+1):
            column = points[start:start+x_points+1]
            print(column)
"""
        points_y = []
        for y in range(1, y_points+1):
            points_y.append((0, y*side_height))
            for xy in points[y::y_points+2]:
                points_y.append(xy)
            points_y.append((self.image.size[0], y*side_height))
        print('Y POINTS', points_y)

        for start in range(0, len(points), y_points+2):
            column = points[start:start+y_points+2]
            print(column)
            for a, b in zip(column[0::1], column[1::1]):
                print(' A', a, ' B', b)
                self.draw.line((a[0], a[1], b[0], b[1]), fill='black', width=1)

        for start in range(0, len(points_y), x_points+2):
            column = points_y[start:start+x_points+2]
            print(column)
            for a, b in zip(column[0::1], column[1::1]):
                print(' A', a, ' B', b)
                self.draw.line((a[0], a[1], b[0], b[1]), fill='black', width=1)
"""


class IndexView(generic.View):
    def get(self, request):
        response = HttpResponse(content_type='image/png')
        #img = Identicon('HELL YEAH!').image
        #img.save(response, 'PNG')
        some = Identicon('purr')
        some.blocks(3, 3)
        some.image.save(response, 'PNG')
        return response





























