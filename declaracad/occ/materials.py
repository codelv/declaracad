"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 24, 2021

@author: jrm
"""
from atom.api import (
    Atom, Float, Bool, Str, Coerced, Value, Enum, Tuple, Typed, FloatRange
)
from enaml.colors import Color, ColorMember


class TextureParameters(Atom):
    """ Texture parametric parameter ranges
    """
    enabled = Bool(True)
    u = Float(0.0, strict=False)
    v = Float(0.0, strict=False)


def coerce_texture(arg):
    if isinstance(arg, dict):
        return TextureParameters(**arg)
    enabled = arg[2] if len(arg) > 2 else True
    return TextureParameters(u=arg[0], v=arg[1], enabled=enabled)


def color_from_rgbf(r: float, g: float, b: float) -> Color:
    """ Create an enaml Color from rgb floats
    """
    return Color(int(r*255), int(g*255), int(b*255))


class Texture(Atom):

    #: Path to the texture file or image
    path = Str()

    #: If given, repeat in the u and v dimension
    repeat = Coerced(TextureParameters,
                     kwargs={'enabled': True, 'u': 1, 'v': 1},
                     coercer=coerce_texture)

    #: If given, adjust th eorigin to the u and v dimension
    origin = Coerced(TextureParameters,
                     kwargs={'enabled': True, 'u': 0, 'v': 0},
                     coercer=coerce_texture)

    #: If given, scale in the u and v dimension
    scale = Coerced(TextureParameters,
                    kwargs={'enabled': True, 'u': 1, 'v': 1},
                    coercer=coerce_texture)


class Fresnel(Atom):
    #: Fresnel style
    model = Enum('constant', 'schlick',  'dielectric', 'conductor')
    params = Value()


class PBRMaterial(Atom):
    #: Internal data
    _data = Value()

    # ---------------------------------------------------------------------
    # BSDF Parameters
    # ---------------------------------------------------------------------
    #: Weight of coat specular/glossy BRDF
    kc = Tuple(Float(strict=False), default=(0.0, 0.0, 0.0))

    #: Weight of base diffuse BRDF
    kd = Tuple(Float(strict=False), default=(0.0, 0.0, 0.0))

    #: Weight of base specular/glossy BRDF
    ks = Tuple(Float(strict=False), default=(0.0, 0.0, 0.0))

    #: Weight of base specular/glossy BTDF
    kt = Tuple(Float(strict=False), default=(0.0, 0.0, 0.0))

    #: Radiance emmited by the surface
    le = Tuple(Float(strict=False), default=(0.0, 0.0, 0.0))

    #: Volume scattering color/density
    absorption = Tuple(Float(strict=False), default=(0.0, 0.0, 0.0))

    #: Fresnel coat
    coat = Typed(Fresnel)

    #: Fresenel base
    base = Typed(Fresnel)

    # ---------------------------------------------------------------------
    # PBR Material Parameters
    # ---------------------------------------------------------------------
    # The base/albedo color
    color = ColorMember()

    #: The roughness coefficent of the material
    roughness = FloatRange(0.0, 1.0)

    #: Modifies metallic coefficient of material in
    metallic = FloatRange(0.0, 1.0)

    #: Modifies light intensity emitted by material
    emission = Tuple(FloatRange(0.0, 1.0), default=(0.0, 0.0, 0.0))


class Material(Atom):
    #: Name
    name = Str()

    #: Internal data
    _data = Value()

    def __init__(self, name="", **kwargs):
        """ Constructor which accepts a material name. Use 'custom'
        to define your own.

        """
        super().__init__(name=name, **kwargs)

    transparency = FloatRange(0.0, 1.0, 0.0)
    shininess = FloatRange(0.0, 1.0, 0.039)
    refraction_index = FloatRange(1.0, 3.0, 1.5)
    #ambient_coef = FloatRange(0.0, 1.0, 0.25)
    #diffuse_coef = FloatRange(0.0, 1.0, 0.25)

    pbr = Typed(PBRMaterial)

    #: Color
    color = ColorMember()
    ambient_color = ColorMember()
    diffuse_color = ColorMember()
    specular_color = ColorMember()
    emissive_color = ColorMember()


Brass = Material(
    name='CUSTOM',
    shininess=0.65,
    refraction_index=1.0,
    ambient_color=color_from_rgbf(0.088428, 0.041081, 0.002090),
    diffuse_color=color_from_rgbf(0.570482, 0.283555, 0.012335),
    specular_color=color_from_rgbf(0.992, 0.941, 0.808),
    emissive_color=Color(0, 0, 0),
    pbr=PBRMaterial(
        ks=(0.985, 0.985, 0.985, 0.045),
        coat=Fresnel(model='constant', params=0),
        base=Fresnel(model='schlick', params=((0.58, 0.42, 0.2),)),
    )
)

Glass = Material(
    name='CUSTOM',
    shininess=0.5,
    transparency=0.8,
    refraction_index=1.62,
    ambient_color=color_from_rgbf(0.263273, 0.290143, 0.290143),
    diffuse_color=color_from_rgbf(0.003936, 0.006571, 0.006571),
    specular_color=color_from_rgbf(0.920, 0.920, 0.920),
    emissive_color=Color(0, 0, 0),
    pbr=PBRMaterial(
        kd=(0.723404, 0.166229, 0.166229),
        absorption=(0.0, 0.0, 0.0, 0.0),
        coat=Fresnel(model='constant', params=0),
        base=Fresnel(model='constant', params=1),
    )
)
