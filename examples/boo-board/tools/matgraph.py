"""matgraph: write UEFN material graphs as Python expressions, build them in ONE MCP round-trip.

    g = Graph("M_Test", "/<root>/Folder")
    t = g.time() * g.scalar("Speed", 1.0)
    g.out("MP_EmissiveColor", g.vector("Tint", (1, .4, 0)) * (t.sin() * .5 + .5))
    g.build()            # creates (or recreates) the material through execute_tool_script

* Numbers become Constant nodes (deduplicated); `a + 2` uses the node's constB property instead (no extra node).
* Identical sub-expressions are shared (hash-consing), so helper functions can be called freely.
* Pin names verified in UEFN 42.30 (`get_expression_input_names`): single-input nodes use "None".
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "cli"))
from uefncli import api  # noqa: E402

_BIN_CONST = {"Add", "Multiply", "Subtract", "Divide", "Min", "Max", "Power"}


class N:
    """A node output. Immutable; hashable by structure."""

    def __init__(self, g, cls, props=(), ins=(), out=""):
        self.g, self.cls, self.props, self.ins, self.o = g, cls, tuple(props), tuple(ins), out
        self.key = (cls, json.dumps(dict(self.props), sort_keys=True), tuple((p, n.key) for p, n in self.ins))

    def at(self, out):
        n = N(self.g, self.cls, self.props, self.ins, out)
        n.key = self.key
        return n

    # ------------------------------------------------------------ arithmetic
    def _bin(self, cls, other, rev=False):
        g = self.g
        if isinstance(other, (int, float)) and not rev and cls in ("Add", "Multiply", "Subtract", "Divide"):
            return g.node(cls, {"constB": float(other)}, A=self)
        if isinstance(other, (int, float)) and rev and cls in ("Add", "Multiply"):
            return g.node(cls, {"constB": float(other)}, A=self)
        o = g.c(other)
        return g.node(cls, {}, A=o, B=self) if rev else g.node(cls, {}, A=self, B=o)

    def __add__(self, o): return self._bin("Add", o)
    def __radd__(self, o): return self._bin("Add", o, True)
    def __sub__(self, o): return self._bin("Subtract", o)
    def __rsub__(self, o): return self._bin("Subtract", o, True)
    def __mul__(self, o): return self._bin("Multiply", o)
    def __rmul__(self, o): return self._bin("Multiply", o, True)
    def __truediv__(self, o): return self._bin("Divide", o)
    def __rtruediv__(self, o): return self._bin("Divide", o, True)
    def __neg__(self): return self * -1.0

    def un(self, cls, props=None):
        return self.g.node(cls, props or {}, _in=self)

    def sin(self): return self.un("Sine")         # period 1: sin(2*pi*x)
    def cos(self): return self.un("Cosine")
    def frac(self): return self.un("Frac")
    def floor(self): return self.un("Floor")
    def abs(self): return self.un("Abs")
    def sat(self): return self.un("Saturate")
    def one_minus(self): return self.un("OneMinus")
    def length(self): return self.un("Length")

    def clamp(self, lo, hi):
        return self.g.node("Clamp", {}, _in=self, Min=self.g.c(lo), Max=self.g.c(hi))

    def min(self, o): return self.g.node("Min", {}, A=self, B=self.g.c(o))
    def max(self, o): return self.g.node("Max", {}, A=self, B=self.g.c(o))
    def pow(self, o): return self.g.node("Power", {}, Base=self, Exp=self.g.c(o))

    def mask(self, ch):
        return self.g.node("ComponentMask", {k: (k in ch) for k in "rgba"}, _in=self)

    @property
    def r(self): return self.mask("r")
    @property
    def gg(self): return self.mask("g")
    @property
    def b(self): return self.mask("b")
    @property
    def a(self): return self.mask("a")
    @property
    def rgb(self): return self.mask("rgb")
    @property
    def rg(self): return self.mask("rg")

    def append(self, o): return self.g.node("AppendVector", {}, A=self, B=self.g.c(o))

    def lerp(self, a, b):
        """self is the alpha: lerp(a, b, self)."""
        return self.g.node("LinearInterpolate", {}, A=self.g.c(a), B=self.g.c(b), Alpha=self)


class Graph:
    def __init__(self, name, folder, domain="MD_Surface", blend="BLEND_Opaque", shading="MSM_DefaultLit",
                 extra=None):
        self.name, self.folder = name, folder
        self.settings = {"materialDomain": domain, "blendMode": blend, "shadingModel": shading}
        self.settings.update(extra or {})
        self.nodes = {}       # key -> (index, cls, props, ins)
        self.order = []
        self.outs = []

    # ------------------------------------------------------------ node factory
    def node(self, cls, props=None, **ins):
        ins = {("None" if k == "_in" else k): v for k, v in ins.items()}
        items = []
        for pin, v in ins.items():
            items.append((pin, self.c(v)))
        n = N(self, cls, sorted((props or {}).items(), key=lambda kv: kv[0]), items)
        if n.key not in self.nodes:
            for _, src in n.ins:
                self._reg(src)
            self._reg(n)
        return n

    def _reg(self, n):
        if n.key not in self.nodes:
            self.nodes[n.key] = (len(self.order), n)
            self.order.append(n)

    def c(self, v):
        if isinstance(v, N):
            return v
        if isinstance(v, (int, float)):
            return self.node("Constant", {"r": float(v)})
        if isinstance(v, (tuple, list)):
            v = [float(x) for x in v]
            if len(v) == 2:
                return self.v2(*v)
            v = v + [1.0] * (4 - len(v))
            return self.node("Constant3Vector", {"constant": {"r": v[0], "g": v[1], "b": v[2], "a": v[3]}})
        raise TypeError(v)

    def v2(self, x, y): return self.node("Constant2Vector", {"r": float(x), "g": float(y)})

    # ------------------------------------------------------------ sources
    def time(self): return self.node("Time")
    def uv(self, index=0): return self.node("TextureCoordinate", {"coordinateIndex": index} if index else {})
    def world_pos(self): return self.node("WorldPosition")
    def local_pos(self): return self.node("LocalPosition")
    def object_pos(self): return self.node("ObjectPositionWS")   # NB: centre of the BOUNDS, not the pivot

    def pivot(self):
        """World position of the mesh origin (pivot). ObjectPositionWS is the bounds centre."""
        return self.node("TransformPosition", {"transformSourceType": "TRANSFORMPOSSOURCE_Local",
                                               "transformType": "TRANSFORMPOSSOURCE_World"}, _in=self.c((0.0, 0.0, 0.0)))
    def vertex_normal(self): return self.node("VertexNormalWS")
    def camera_vector(self): return self.node("CameraVectorWS")

    def scalar(self, name, default, group=None, prio=0):
        p = {"parameterName": name, "defaultValue": float(default)}
        if group:
            p["group"] = group
            p["sortPriority"] = prio
        return self.node("ScalarParameter", p)

    def vector(self, name, rgba, group=None, prio=0):
        r = list(rgba) + [1.0] * (4 - len(rgba))
        p = {"parameterName": name, "defaultValue": {"r": r[0], "g": r[1], "b": r[2], "a": r[3]}}
        if group:
            p["group"] = group
            p["sortPriority"] = prio
        return self.node("VectorParameter", p)

    def texture(self, name, texture_path, uvs=None, sampler="SAMPLERTYPE_Color", group=None):
        p = {"parameterName": name, "texture": {"refPath": texture_path}, "samplerType": sampler}
        if group:
            p["group"] = group
        if uvs is None:
            return self.node("TextureSampleParameter2D", p)
        return self.node("TextureSampleParameter2D", p, UVs=uvs)

    def local_to_world_vec(self, v):
        return self.node("Transform", {"transformSourceType": "TRANSFORMSOURCE_Local",
                                       "transformType": "TRANSFORM_World"}, _in=v)

    def smoothstep(self, lo, hi, x):
        return self.node("SmoothStep", {}, Min=self.c(lo), Max=self.c(hi), Value=x)

    def rotate_about_axis(self, axis, angle, pivot, position):
        """angle in turns (1 = 360 deg), as UE's RotateAboutAxis expects. Returns the OFFSET to add to WPO."""
        return self.node("RotateAboutAxis", {}, NormalizedRotationAxis=self.c(axis), RotationAngle=self.c(angle),
                         PivotPoint=pivot, Position=position)

    def out(self, prop, n):
        self.outs.append((prop, self.c(n)))

    # ------------------------------------------------------------ build
    def plan(self):
        idx = {n.key: i for i, n in enumerate(self.order)}
        nodes, links = [], []
        for i, n in enumerate(self.order):
            nodes.append([n.cls, dict(n.props)])
            for pin, src in n.ins:
                links.append([idx[src.key], src.o, i, pin])
        outs = [[idx[n.key], n.o, prop] for prop, n in self.outs]
        return {"folder": self.folder, "name": self.name, "settings": self.settings,
                "nodes": nodes, "links": links, "outs": outs}

    def build(self, recompile=True):
        plan = self.plan()
        plan["recompile"] = recompile
        script = SANDBOX + "\nPLAN = json.loads(" + repr(json.dumps(plan)) + ")\n"
        r = api.tool("script", "execute_tool_script", {"script": script})
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except ValueError:
                pass
        return r


SANDBOX = r'''
import json
MT = "editor_toolset.toolsets.material.MaterialTools."
OT = "editor_toolset.toolsets.object.ObjectTools."
AT = "editor_toolset.toolsets.asset.AssetTools."

def T(n, a):
    return execute_tool(n, json.dumps(a))

def rv(r):
    return r["returnValue"] if isinstance(r, dict) and "returnValue" in r else r

def run():
    P = PLAN
    path = P["folder"] + "/" + P["name"]
    errs = []
    if rv(T(AT + "exists", {"path": path})):
        m = {"refPath": path + "." + P["name"]}
        for e in rv(T(MT + "get_expressions", {"material_or_function": m})) or []:
            T(MT + "delete_expression", {"material_or_function": m, "expression": e})
    else:
        m = rv(T(MT + "create_material", {"folder_path": P["folder"], "asset_name": P["name"]}))
    T(OT + "set_properties", {"instance": m, "values": json.dumps(P["settings"])})
    refs = []
    for i, (cls, props) in enumerate(P["nodes"]):
        e = rv(T(MT + "add_expression", {"material_or_function": m,
               "expression_class": {"refPath": "/Script/Engine.MaterialExpression" + cls},
               "x": -400 - 220 * (i % 12), "y": 120 * (i // 12)}))
        if props:
            try:
                T(OT + "set_properties", {"instance": e, "values": json.dumps(props)})
            except Exception as ex:
                errs.append("props %d %s: %s" % (i, cls, str(ex)[:160]))
        refs.append(e)
    for s, so, d, pin in P["links"]:
        try:
            T(MT + "connect_expressions", {"from_expression": refs[s], "from_output_name": so,
                                           "to_expression": refs[d], "to_input_name": pin})
        except Exception as ex:
            errs.append("link %d->%d.%s: %s" % (s, d, pin, str(ex)[:160]))
    for s, so, prop in P["outs"]:
        T(MT + "connect_to_output", {"expression": refs[s], "output_name": so, "material_property": prop})
    T(MT + "layout_expressions", {"material_or_function": m})
    res = None
    if P.get("recompile", True):
        try:
            res = T(MT + "recompile", {"material_or_function": m})
        except Exception as ex:
            errs.append("recompile: " + str(ex)[:1500])
    return {"material": m, "nodes": len(refs), "links": len(P["links"]), "errors": errs, "recompile": str(res)[:500]}
'''
