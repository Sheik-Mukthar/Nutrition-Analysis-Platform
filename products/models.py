# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError

from ingredients.models import Ingredient

not_negative = MinValueValidator(0)

# Schema overview:
# Supplier  - just a name, maybe tags like online/bulk/etc
# Price     - _ingredient_ at _supplier_, at a _price_ for a _weight_
#           TODO - track historic prices or not?
# Product   - Deprecated - prices are on to ingredients directly now

class Supplier(models.Model):
   """
   A place where ingredients may be purchased.
   Mainly just an anchor for price
   """

   name = models.CharField(
      max_length=settings.NAME_LENGTH,
      blank=False,
      unique=True,
   )
   slug = models.CharField(
      max_length=settings.SLUG_LENGTH,
      blank=False,
      unique=True,
   )
   description = models.CharField(max_length=settings.DESCR_LENGTH,blank=True)
   # TODO tags ("online", "bulk", "supermarket" etc) ?

   def __str__(self):
      return self.name

   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   @cached_property
   def product_count(self):
      """
      Number of items this supplier has prices listed for
      """
      return Ingredient.objects.filter(price__supplier=self).distinct().count()


class Product(models.Model):
   """
   PRODUCT IS DEPRECATED AND MAY BE REMOVED IN A FUTURE RELEASE
   A branded product; a specific instance of a generic ingredient.
   Currently has no use except to attach brand names to ingredients.
   """

   class Meta:
      ordering = ["-updated_at"]
      unique_together = ("name", "brand")

   name = models.CharField(
      max_length=settings.NAME_LENGTH,
      blank=False,
      unique=False,   # NOTE name and brand unique together, but name not unique
   )
   slug = models.CharField(
      max_length=settings.SLUG_LENGTH,
      blank=True,    # Set automatically; null=False still applies
      unique=True,
   )
   brand = models.CharField(max_length=settings.NAME_LENGTH,blank=False)

   description = models.CharField(max_length=settings.DESCR_LENGTH,blank=True)

   ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   def __str__(self):
      return "%s (%s)"%(self.name,self.brand)

   def save(self, *args, **kwargs):
      if not self.slug:
         self.slug = slugify("%s_%s"%(self.brand, self.name)) # NOTE will Exception on clash
      super(Product, self).save(*args, **kwargs)


class Price(models.Model):
   """
   Price of an Ingredient
   and the Weight
   at a Supplier
   on a Date
   """

   supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
   ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

   price = models.DecimalField(
      decimal_places=2,
      max_digits=6,
      validators=[not_negative],
   )
   weight = models.DecimalField(
      decimal_places=3,
      max_digits=6,
      validators=[not_negative],
   )

   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   def __str__(self):
      return "%s@%s $%f/kg"%(self.ingredient,self.supplier,self.per_kg) # FIXME -> ingredient

   @cached_property
   def per_kg(self):
      """
      Returns price per kg - for display use
      """
      try:
         return self.price/self.weight
      except TypeError:
         return None
