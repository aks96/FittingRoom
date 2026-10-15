"""Category routing, uncertainty and garment-only analysis boundary tests."""
import unittest
import numpy as np
from PIL import Image
from local_ai.garment_details import garment_view,detail_suggestions
from local_ai.garment_catalog import native_category,compatibility_error

class GarmentDetailsTests(unittest.TestCase):
    def test_bottoms_and_one_pieces_use_native_model_categories(self):
        for category in ('Pants','Jeans','Shorts','Skirt'):self.assertEqual(native_category(category),'bottoms')
        for category in ('Dress','Jumpsuit'):self.assertEqual(native_category(category),'one-pieces')
        for category in ('Top','Shirt','T-shirt','Sweater','Hoodie','Jacket'):self.assertEqual(native_category(category),'tops')
        for category in ('Unsupported','Shoes','Full outfit','../pants'):
            with self.assertRaises(ValueError):native_category(category)

    def test_matching_declared_profiles_and_unisex(self):
        for profile in ('Women','Men'):
            self.assertIsNone(compatibility_error(profile,profile))
            self.assertIsNone(compatibility_error('Unisex',profile))
        self.assertIn('selected wearer profile is Men',compatibility_error('Women','Men'))
        self.assertIn('selected wearer profile is Women',compatibility_error('Men','Women'))
        self.assertIsNotNone(compatibility_error('Unisex',None))
        self.assertIsNotNone(compatibility_error('Uncertain','Women'))

    def test_retailer_face_and_skin_are_excluded_from_detail_crop(self):
        pixels=np.full((20,20,3),255,dtype=np.uint8);mask=np.zeros((20,20),dtype=np.uint8)
        pixels[:5]=[255,0,0];mask[:5]=1 # face must never determine clothing range
        pixels[8:18,4:16]=[0,0,200];mask[8:18,4:16]=3
        pixels[10:12,7:9]=[0,255,0];mask[10:12,7:9]=12 # skin inside bounding box
        view=garment_view(Image.fromarray(pixels),mask,'Shirt')
        data=np.array(view);self.assertEqual(view.size,(12,10))
        self.assertFalse(np.any(np.all(data==[255,0,0],axis=2)))
        self.assertFalse(np.any(np.all(data==[0,255,0],axis=2)))
        self.assertTrue(np.any(np.all(data==[0,0,200],axis=2)))

    def test_lower_garment_crop_excludes_top_and_finds_skirt_label(self):
        pixels=np.zeros((20,20,3),dtype=np.uint8);mask=np.zeros((20,20),dtype=np.uint8)
        mask[2:8]=3;mask[10:19,5:15]=5
        view=garment_view(Image.fromarray(pixels),mask,'Skirt')
        self.assertEqual(view.size,(10,9))
        self.assertIsNone(garment_view(Image.fromarray(pixels),mask,'Pants'))

    def test_flat_lay_can_use_foreground_but_model_photo_cannot(self):
        pixels=np.full((20,20,3),255,dtype=np.uint8);pixels[5:15,5:15]=[30,30,80]
        image=Image.fromarray(pixels);mask=np.zeros((20,20),dtype=np.uint8)
        self.assertIsNone(garment_view(image,mask,'Top','model'))
        self.assertEqual(garment_view(image,mask,'Top','flat-lay').size,(10,10))

    def test_ambiguous_visual_cues_never_become_certain_composition(self):
        for isolated,scores in [(False,{'fabric':(0,.9),'audience':(1,.9)}),(True,{'fabric':(0,.01),'audience':(1,.01)})]:
            details=detail_suggestions(scores,isolated)
            self.assertEqual(details['audience'],'Uncertain');self.assertEqual(details['fabricAppearance'],'Uncertain')
            self.assertIn('Not determined',details['material'])
            self.assertTrue(details['audienceReview']);self.assertTrue(details['fabricReview'])

if __name__=='__main__':unittest.main()
