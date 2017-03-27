#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 DevicePilot Ltd.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from synth.utils import hashIt

femaleNames=["Amelia","Olivia","Isla","Emily","Poppy","Ava","Isabella","Jessica","Lily","Sophie","Grace","Sophia","Mia","Evie","Ruby","Ella","Scarlett","Isabelle","Chloe","Sienna","Freya","Phoebe","Charlotte","Daisy","Alice","Florence","Eva","Sofia","Millie","Lucy","Evelyn","Elsie","Rosie","Imogen","Lola","Matilda","Elizabeth","Layla","Holly","Lilly","Molly","Erin","Ellie","Maisie","Maya","Abigail","Eliza","Georgia","Jasmine","Esme","Willow","Bella","Annabelle","Ivy","Amber","Emilia","Emma","Summer","Hannah","Eleanor","Harriet","Rose","Amelie","Lexi","Megan","Gracie","Zara","Lacey","Martha","Anna","Violet","Darcey","Maria","Maryam","Brooke","Aisha","Katie","Leah","Thea","Darcie","Hollie","Amy","Mollie","Heidi","Lottie","Bethany","Francesca","Faith","Harper","Nancy","Beatrice","Isabel","Darcy","Lydia","Sarah","Sara","Julia","Victoria","Zoe","Robyn"]

maleNames=["Oliver","Jack","Harry","Jacob","Charlie","Thomas","George","Oscar","James","William","Noah","Alfie","Joshua","Muhammad","Henry","Leo","Archie","Ethan","Joseph","Freddie","Samuel","Alexander","Logan","Daniel","Isaac","Max","Mohammed","Benjamin","Mason","Lucas","Edward","Harrison","Jake","Dylan","Riley","Finley","Theo","Sebastian","Adam","Zachary","Arthur","Toby","Jayden","Luke","Harley","Lewis","Tyler","Harvey","Matthew","David","Reuben","Michael","Elijah","Kian","Tommy","Mohammad","Blake","Luca","Theodore","Stanley","Jenson","Nathan","Charles","Frankie","Jude","Teddy","Louie","Louis","Ryan","Hugo","Bobby","Elliott","Dexter","Ollie","Alex","Liam","Kai","Gabriel","Connor","Aaron","Frederick","Callum","Elliot","Albert","Leon","Ronnie","Rory","Jamie","Austin","Seth","Ibrahim","Owen","Caleb","Ellis","Sonny","Robert","Joey","Felix","Finlay","Jackson"]

lastNames = ["Adams","Aigner","Allen","Andersen","Anderson","André","Andreassen","Angelopoulos","Antoniou","Athanasiadis","Auer","Babić","Bailey","Baker","Bakker","Barbieri","Barišić","Barnes","Bauer","Baumgartner","Becker","Bell","Bennett","Berg","Berger","Bernard","Bertrand","Bianchi","Binder","Blažević","Bogdanov","Bonnet","Bos","Bošnjak","Božić","Brooks","Brouwer","Brown","Brunner","Bruno","Butler","Campbell","Carter","Caruso","Christensen","Christiansen","Claes","Clark","Clarke","Collins","Colombo","Conti","Cook","Cooper","Costa","Cox","Cruz","Dahl","David","Davies","Davis","De Boer","De Graaf","De Groot","De Jong","De Luca","De Smet","De Vries","De Wit","Dekker","Diaz","Dijkstra","Dimitriadis","Dubois","Dubois","Dupont","Durand","Ebner","Eder","Edwards","Egger","Eriksen","Esposito","Evans","Ferrari","Filipović","Fischer","Fisher","Flores","Fontana","Foster","Fournier","François","Fuchs","Gallo","Garcia","Garcia","Georgiou","Giordano","Girard","Golubev","Gomez","Gonzalez","Goossens","Gray","Greco","Green","Grgić","Gruber","Gutierrez","Haas","Hagen","Hall","Halvorsen","Hansen","Harris","Haugen","Heilig","Hendriks","Henriksen","Hernandez","Hill","Hofer","Hoffmann","Horvat","Howard","Huber","Hughes","Ivanov","Jackson","Jacobs","Jacobsen","James","Jansen","Janssen","Janssens","Jenkins","Jensen","Johannessen","Johansen","Johnsen","Johnson","Jones","Jørgensen","Jukić","Jurić","Karlsen","Kelly","King","Knežević","Koller","Kovač","Kovačević","Kovačić","Kozlov","Kristiansen","Kuznetsov","Lambert","Lang","Larsen","Laurent","Lebedev","Lechner","Lee","Lefebvre","Lefèvre","Lehner","Leitner","Leroy","Lewis","Lombardi","Long","Lopez","Lovrić","Lund","Madsen","Maes","Maier","Mancini","Mariani","Marić","Marino","Marković","Martin","Martinez","Martinez","Matić","Mayer","Mayr","Meijer","Meyer","Mercier","Mertens","Meyer","Michel","Miller","Mitchell","Møller","Moore","Morales","Moreau","Morel","Moretti","Morgan","Morozov","Morris","Mortensen","Moser","Mulder","Müller","Murphy","Myers","Nelson","Nguyen","Nielsen","Nikolaidis","Nilsen","Novak","Novikov","Olsen","Ortiz","Panagiotopoulos","Papadakis","Papadopoulos","Papantoniou","Parker","Pavić","Pavlov","Pavlović","Pedersen","Peeters","Perez","Perić","Perković","Perry","Peters","Petersen","Peterson","Petit","Petridis","Petrov","Petrović","Pettersen","Phillips","Pichler","Popov","Popović","Poulsen","Powell","Price","Radić","Ramirez","Rasmussen","Reed","Reiter","Reyes","Ricci","Richard","Richardson","Rinaldi","Rivera","Rizzo","Robert","Roberts","Robinson","Rodriguez","Rogers","Romano","Ross","Rossi","Roux","Russell","Russo","Sanchez","Sanders","Santoro","Šarić","Schmid","Schmidt","Schneider","Schulz","Schuster","Schwarz","Scott","Semyonov","Simon","Simon","Smirnov","Smit","Smith","Smits","Sokolov","Solovyov","Sørensen","Steiner","Stewart","Sullivan","Taylor","Thomas","Thompson","Thomsen","Tomić","Torres","Turner","Van den Berg","Van der Meer","Van Dijk","Van Leeuwen","Vasilyev","Vidović","Vincent","Vinogradov","Visser","Vlahos","Volkov","Vorobyov","Vos","Vuković","Wagner","Walker","Wallner","Ward","Watson","Weber","White","Willems","Williams","Wilson","Wimmer","Winkler","Wolf","Wood","Wouters","Wright","Young","Zaytsev"]

def firstName(r):
    if hashIt(r,1):
        first = femaleNames
    else:
        first = maleNames
    return first[hashIt(r,len(first))]

def lastName(r):
    return lastNames[hashIt(r,len(lastNames))]

def fullName(r):
    return firstName(r) + " " + lastName(r)
