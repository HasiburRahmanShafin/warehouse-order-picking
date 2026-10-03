"""
Warehouse grid with one-way aisles.

Coordinates are (x, y): x = column (left to right), y = row (bottom to top).
Layout, from bottom to top:
    cross-aisle row  (two-way, robots move left/right)
    block of aisle rows  (racks + one-way vertical aisles)
    cross-aisle row
    ... (repeat for each block)
"""
from dataclasses import dataclass

Cell = tuple[int, int]

UP, DOWN = 1, -1


@dataclass
class Warehouse:
    width: int
    height: int
    blocked: set[Cell]          # rack cells (robots can't enter)
    aisle_dir: dict[int, int]   # aisle column x -> UP or DOWN (empty dict = two-way)
    cross_rows: set[int]        # y values of cross-aisle rows
    depot: Cell

    def is_free(self, c: Cell) -> bool:
        x, y = c
        return 0 <= x < self.width and 0 <= y < self.height and c not in self.blocked

    def _vertical_move_allowed(self, frm: Cell, to: Cell) -> bool:
        direction = self.aisle_dir.get(frm[0])
        if direction is None:          # two-way warehouse
            return True
        dy = to[1] - frm[1]
        return dy == direction         # must follow the aisle's arrow

    def neighbors(self, c: Cell) -> list[Cell]:
        """Cells a robot standing on c may move to in one step (respects one-way rules)."""
        x, y = c
        result = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if not self.is_free(n):
                continue
            if dy != 0 and not self._vertical_move_allowed(c, n):
                continue
            result.append(n)
        return result

    def free_cells(self) -> list[Cell]:
        return [(x, y) for y in range(self.height) for x in range(self.width) if self.is_free((x, y))]

    def pick_cells(self) -> list[Cell]:
        """Aisle cells next to a rack: where a robot stops to pick an item."""
        picks = []
        for (x, y) in self.free_cells():
            if y in self.cross_rows:
                continue
            if (x - 1, y) in self.blocked or (x + 1, y) in self.blocked:
                picks.append((x, y))
        return picks

    def render(self) -> str:
        """Text picture of the warehouse (top row printed first)."""
        lines = []
        for y in reversed(range(self.height)):
            row = ""
            for x in range(self.width):
                c = (x, y)
                if c == self.depot:
                    row += "D"
                elif c in self.blocked:
                    row += "#"
                elif y in self.cross_rows:
                    row += "."
                elif x in self.aisle_dir:
                    row += "^" if self.aisle_dir[x] == UP else "v"
                else:
                    row += "|"   # two-way aisle
            lines.append(row)
        return "\n".join(lines)


def build_warehouse(n_aisles: int = 6, aisle_width: int = 1, aisle_length: int = 10,
                    n_blocks: int = 1, one_way: bool = True) -> Warehouse:
    """
    n_aisles     : number of vertical aisles
    aisle_width  : 1 = narrow aisle (single lane), 2+ = wide aisle
    aisle_length : rows of racks per block
    n_blocks     : blocks of racks stacked vertically (each separated by a cross-aisle)
    one_way      : True = aisles alternate UP/DOWN; False = all aisles two-way
    """
    if one_way and n_aisles < 2:
        raise ValueError("One-way layout needs at least 2 aisles, otherwise robots get stuck.")

    # --- columns: rack(1) | aisle | rack(2) | aisle | ... | aisle | rack(1)
    is_rack_col = []
    aisle_dir = {}
    is_rack_col.append(True)                       # outer rack on the left
    for a in range(n_aisles):
        direction = UP if a % 2 == 0 else DOWN     # alternate directions
        for _ in range(aisle_width):
            if one_way:
                aisle_dir[len(is_rack_col)] = direction
            is_rack_col.append(False)
        rack_w = 2 if a < n_aisles - 1 else 1      # back-to-back racks inside, single at edge
        is_rack_col.extend([True] * rack_w)
    width = len(is_rack_col)

    # --- rows: cross | block | cross | block | ... | cross
    cross_rows = {0}
    y = 1
    for _ in range(n_blocks):
        y += aisle_length
        cross_rows.add(y)
        y += 1
    height = y

    blocked = {(x, y) for x in range(width) for y in range(height)
               if y not in cross_rows and is_rack_col[x]}

    first_aisle_x = 1
    depot = (first_aisle_x, 0)                     # bottom-left, on the cross-aisle
    return Warehouse(width, height, blocked, aisle_dir, cross_rows, depot)


if __name__ == "__main__":
    print("NARROW (aisle_width=1), one-way:")
    print(build_warehouse(n_aisles=4, aisle_width=1, aisle_length=6).render())
    print("\nWIDE (aisle_width=2), one-way:")
    print(build_warehouse(n_aisles=4, aisle_width=2, aisle_length=6).render())