import math
def calculate_circle_area(radius):
    "calculater the area of a cricle give its radius"
    if radius<0:
        return"Radius cannot be negative"
    return math .pi*(radius**2)
def calculate_retangle_area(length,width):
    "calculatese the area of a rectangle give its length and width"
    if length <0 or width <0:
        return "dimensios connot be negative"
    return length *width
def calclate_triangle_area(base,height):
    "calculater the area of a triangle given its base and height"
    if base <0 or height <0:
        return"Dimensions cannot be negative"
    return 0.5* base *height
    if _name_=="_main_":
     r=5
    circle_area= calculate_circle_area (r)
    print (f"Area of circle with radius {r} is:{circle_area :2f }")
    l,w=10,4
    rectangle_area=calculate_rectangle_area(l,w)
    print (f"Area of rectangle with length {1}and width {w}is:{rect_area}")
    b,h=6,8
    triangle_area=calculate_triangle_area(b,h)
    print (f"Area of traiangle with base {b} and hight {h} is :{tri_area}")