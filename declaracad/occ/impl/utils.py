"""
Copyright (c) 2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from OCCT import Graphic3d
from OCCT.Graphic3d import (Graphic3d_BSDF, Graphic3d_Fresnel,
                            Graphic3d_MaterialAspect, Graphic3d_PBRMaterial,
                            Graphic3d_Vec3, Graphic3d_Vec4)
from OCCT.Quantity import Quantity_Color, Quantity_TOC_RGB

OCC_COLOR_CACHE = {}
OCC_MATERIAL_CACHE = {}


def color_to_quantity_color(color):
    """Convert an enaml color to an Quantity_Color. The result is cached.

    Parameters
    ----------
    color: enaml.colors.Color
        The color to convert

    Returns
    -------
    result: (Quantity_Color, float or None)
        A tuple of the color and transparency
    """
    result = OCC_COLOR_CACHE.get(color.argb)
    if result is None:
        transparency = None if color.alpha == 255 else 1 - color.alpha / 255.0
        occ_color = Quantity_Color(
            color.red / 255.0, color.green / 255.0, color.blue / 255.0, Quantity_TOC_RGB
        )
        result = (occ_color, transparency)
        OCC_COLOR_CACHE[color.argb] = result
    return result


def fresnel_to_g3d_fresnel(fresnel):
    """Create a Graphic3d_Fresnel from the declaracad Fresnel definition

    Parameters
    ----------
    material: declaracad.occ.materials.Fresnel
        The fresnel definition

    Returns
    -------
    result: Graphic3d_Fresnel
        The fresnel

    """
    model = fresnel.model.title()
    CreateFresnel = getattr(Graphic3d_Fresnel, f"Create{model}_")
    # Convert tuple arguments to G3d Vec
    params = fresnel.params
    if not isinstance(fresnel.params, (tuple, list)):
        params = [params]
    args = (
        Graphic3d_Vec3(*param) if isinstance(param, tuple) else param
        for param in params
    )
    return CreateFresnel(*args)


def create_pbr_material(material):
    """Create a Graphic3d_PBRMaterial from the declaracad Material definition

    Parameters
    ----------
    material: declaracad.occ.materials.Material
        The material definition

    Returns
    -------
    result: Graphic3d_PBRMaterial
        The material

    """
    d = material.pbr
    if d._data is not None:
        return d._data

    bsdf = Graphic3d_BSDF()
    bsdf.Kd = Graphic3d_Vec3(*d.kd)
    bsdf.Kt = Graphic3d_Vec3(*d.kt)
    bsdf.Le = Graphic3d_Vec3(*d.le)

    if len(d.kc) == 4:
        *v, w = d.kc
        bsdf.Kc = Graphic3d_Vec4(Graphic3d_Vec3(*v), w)
    else:
        bsdf.Kc = Graphic3d_Vec4(Graphic3d_Vec3(*d.kc))

    if len(d.ks) == 4:
        *v, w = d.ks
        bsdf.Ks = Graphic3d_Vec4(Graphic3d_Vec3(*v), w)
    else:
        bsdf.Ks = Graphic3d_Vec4(Graphic3d_Vec3(*d.ks))

    if len(d.absorption) == 4:
        *v, w = d.absorption
        bsdf.Absorption = Graphic3d_Vec4(Graphic3d_Vec3(*v), w)
    else:
        bsdf.Absorption = Graphic3d_Vec4(Graphic3d_Vec3(*d.absorption))

    if d.coat:
        bsdf.FresnelCoat = fresnel_to_g3d_fresnel(d.coat)
    if d.base:
        bsdf.FresnelBase = fresnel_to_g3d_fresnel(d.base)

    mat = d._data = Graphic3d_PBRMaterial(bsdf)
    mat.SetEmission(Graphic3d_Vec3(*d.emission))
    mat.SetRoughness(d.roughness)
    mat.SetMetallic(d.metallic)
    if d.color:
        c, t = color_to_quantity_color(d.color)
        mat.SetColor(c)
        if t is not None:
            mat.SetAlpha(t)

    return mat


def material_to_material_aspect(material):
    """Convert a material name to a Graphic3d material

    Parameters
    ----------
    material: declaracad.occ.materials.Material
        The material definition

    Returns
    -------
    result: Graphic3d_MaterialAspect or None
        The material

    """
    if material is None or not material.name:
        name = "CHARCOAL"
    else:
        name = material.name.upper()
        if name == "ALUMINUM":
            name = "ALUMINIUM"
    if name == "CUSTOM":
        if material._data is not None:
            return material._data  # Cached value
        a = material._data = Graphic3d_MaterialAspect(
            Graphic3d.Graphic3d_NameOfMaterial_UserDefined
        )
        a.SetMaterialType(Graphic3d.Graphic3d_MATERIAL_PHYSIC)
        if material.transparency:
            a.SetTransparency(material.transparency)
        a.SetShininess(material.shininess)
        a.SetRefractionIndex(material.refraction_index)

        if material.pbr is not None:
            mat = create_pbr_material(material)
            a.SetPBRMaterial(mat)

        if material.color:
            c, t = color_to_quantity_color(material.color)
            a.SetColor(c)
        if material.ambient_color:
            c, t = color_to_quantity_color(material.ambient_color)
            a.SetAmbientColor(c)
        if material.diffuse_color:
            c, t = color_to_quantity_color(material.diffuse_color)
            a.SetDiffuseColor(c)
        if material.specular_color:
            c, t = color_to_quantity_color(material.specular_color)
            a.SetSpecularColor(c)
        if material.emissive_color:
            c, t = color_to_quantity_color(material.emissive_color)
            a.SetEmissiveColor(c)

        return a
    ma = OCC_MATERIAL_CACHE.get(name)
    if ma is None:
        material_type = "Graphic3d_NOM_%s" % name
        ma = Graphic3d_MaterialAspect(getattr(Graphic3d, material_type))
        OCC_MATERIAL_CACHE[name] = ma
    return ma
