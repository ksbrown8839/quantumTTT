
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Set
from quantum_coin import QuantumCoin

import tkinter as tk
from tkinter import messagebox
import sys



UI_SCALE = 1.8
@dataclass
class Move:
    player: str
    index: int
    cells: Tuple[int, int]
    collapsed_to: Optional[int] = None


class QuantumTicTacToeLogic:
    """Game mechanics for Quantum Tic-Tac-Toe."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.moves: List[Move] = []
        self.collapsed_board: List[Optional[Tuple[str, int]]] = [None] * 9
        self.move_counter = {'X': 0, 'O': 0}
        self.current_player: str = 'X'
        self.mode: str = 'PLAY'
        self.collapse_chooser: Optional[str] = None
        self.cycle_creator: Optional[str] = None
        self.next_player_after_collapse: Optional[str] = None
        self.collapse_moves: List[Move] = []
        self.collapse_index: int = 0

    @staticmethod
    def other_player(p: str) -> str:
        return 'O' if p == 'X' else 'X'

    def build_adjacency(self, moves: List[Move]) -> Dict[int, Set[int]]:
        """Build adjacency among squares touched by moves."""
        adj: Dict[int, Set[int]] = {}
        for m in moves:
            a, b = m.cells
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
        return adj
    
    def get_connected_component(self, adj: Dict[int, Set[int]], start_node: int) -> Set[int]:
        """Return all squares in the connected component of start_node."""
        component = set()
        stack = [start_node]
        while stack:
            node = stack.pop()
            if node not in component:
                component.add(node)
                for neighbor in adj.get(node, []):
                    if neighbor not in component:
                        stack.append(neighbor)
        return component

    def bfs_reachable(self, adj: Dict[int, Set[int]], start: int, target: int) -> bool:
        """Check if target is reachable from start in the current graph."""
        if start == target:
            return True
        from collections import deque

        q = deque([start])
        visited = {start}
        while q:
            u = q.popleft()
            for v in adj.get(u, []):
                if v == target:
                    return True
                if v not in visited:
                    visited.add(v)
                    q.append(v)
        return False

    def would_create_loop(self, new_cells: Tuple[int, int]) -> bool:
        """Return True if adding new_cells would create a cycle."""
        a, b = new_cells
        adj = self.build_adjacency(self.moves)
        return self.bfs_reachable(adj, a, b)

    def add_spooky_move(self, cell1: int, cell2: int):
        """Add a spooky move and trigger collapse if a loop forms."""
        assert self.mode == 'PLAY'
        assert cell1 != cell2
        loop = self.would_create_loop((cell1, cell2))
        self.move_counter[self.current_player] += 1
        idx = self.move_counter[self.current_player]
        mv = Move(self.current_player, idx, (cell1, cell2))
        self.moves.append(mv)

        if loop:
            self.cycle_creator = self.current_player
            self.collapse_chooser = self.other_player(self.current_player)
            self.next_player_after_collapse = self.collapse_chooser
            adj = self.build_adjacency(self.moves)
            involved_squares = self.get_connected_component(adj, cell1)
            to_collapse = []
            to_keep = []

            for m in self.moves:
                if m.cells[0] in involved_squares:
                    to_collapse.append(m)
                else:
                    to_keep.append(m)

            self.collapse_moves = to_collapse
            self.moves = to_keep

            self.mode = 'COLLAPSE'
            self.collapse_index = 0
            for i, m in enumerate(self.collapse_moves):
                if m is mv:
                    self.collapse_index = i
                    break

        else:
            self.current_player = self.other_player(self.current_player)

    def collapse_step(self, chosen_cell: int) -> bool:
        """
        Perform one collapse selection for the current move in collapse_moves.
        After each selection, automatically collapse any moves that now have only
        one valid square left (forced moves), and advance collapse_index to the
        next uncollapsed move.
        """
        assert self.mode == 'COLLAPSE'
        if self.collapse_index >= len(self.collapse_moves):
            return True

        mv = self.collapse_moves[self.collapse_index]

        if chosen_cell not in mv.cells:
            return False
        if self.collapsed_board[chosen_cell] is not None:
            return False

        mv.collapsed_to = chosen_cell
        self.collapsed_board[chosen_cell] = (mv.player, mv.index)

        changed = True
        while changed:
            changed = False
            for m in self.collapse_moves:
                if m.collapsed_to is None:
                    free = [c for c in m.cells if self.collapsed_board[c] is None]
                    if len(free) == 1:
                        m.collapsed_to = free[0]
                        self.collapsed_board[free[0]] = (m.player, m.index)
                        changed = True

        while (
            self.collapse_index < len(self.collapse_moves)
            and self.collapse_moves[self.collapse_index].collapsed_to is not None
        ):
            self.collapse_index += 1

        if self.collapse_index >= len(self.collapse_moves):
            self.mode = 'PLAY'
            if self.next_player_after_collapse:
                self.current_player = self.next_player_after_collapse

        return True




    def check_winner(self):
        """
        Check classical board for 3-in-a-row.
        Returns:
          - None                  : no winner yet
          - ('DRAW', None, sum)   : tie with equal smallest index sum
          - ('X', line, sum)      : X uniquely wins
          - ('O', line, sum)      : O uniquely wins
          - ('X', line, sum, ('O', o_line, o_sum)) : both win, X wins tiebreak
          - ('O', line, sum, ('X', x_line, x_sum)) : both win, O wins tiebreak
        """
        lines = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        wins = {'X': [], 'O': []}

        for a, b, c in lines:
            ca = self.collapsed_board[a]
            cb = self.collapsed_board[b]
            cc = self.collapsed_board[c]
            if ca and cb and cc:
                pa, ia = ca
                pb, ib = cb
                pc, ic = cc
                if pa == pb == pc:
                    s = ia + ib + ic
                    wins[pa].append(((a, b, c), s))

        if not wins['X'] and not wins['O']:
            return None

        if wins['X'] and not wins['O']:
            line, s = min(wins['X'], key=lambda t: t[1])
            return 'X', line, s

        if wins['O'] and not wins['X']:
            line, s = min(wins['O'], key=lambda t: t[1])
            return 'O', line, s

        x_line, x_sum = min(wins['X'], key=lambda t: t[1])
        o_line, o_sum = min(wins['O'], key=lambda t: t[1])

        if x_sum < o_sum:
            return 'X', x_line, x_sum, ('O', o_line, o_sum)
        elif o_sum < x_sum:
            return 'O', o_line, o_sum, ('X', x_line, x_sum)
        else:
            return 'DRAW', None, x_sum


class QuantumTicTacToeGUI:
    """
    Tkinter interface for playing Quantum Tic-Tac-Toe, using a Canvas board.

    - Click squares to choose spooky pairs.
    - Collapse phase is unchanged (click one of the two squares).
    - Spooky pairs are connected by colored lines on the canvas.
    """

    def __init__(self, root: tk.Tk, scale: float = UI_SCALE, force_aer: bool = False):
        self.root = root
        self.root.title("Quantum Tic-Tac-Toe")

        self.scale = scale
        self.root.tk.call("tk", "scaling", self.scale)

        self.logic = QuantumTicTacToeLogic()

        self.use_quantum_collapse = True
        self.quantum_coin = QuantumCoin(
            backend_name="ibm_torino",
            aer_backend_name="aer_simulator",
            shots=256,
            force_aer=force_aer
        )

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            root,
            textvariable=self.status_var,
            font=("Arial", int(12 * self.scale)),
            wraplength=int(280 * self.scale),
            justify="left",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, pady=int(5 * self.scale))

        self.canvas_size = int(300 * self.scale)
        self.cell_size = self.canvas_size // 3
        self.margin = int(4 * self.scale)

        self.board_canvas = tk.Canvas(
            root,
            width=self.canvas_size,
            height=self.canvas_size,
            bg="#eeeeee",
            highlightthickness=0,
        )
        self.board_canvas.grid(
            row=1,
            column=0,
            padx=int(5 * self.scale),
            pady=int(5 * self.scale),
        )

        self.board_canvas.bind("<Button-1>", self.on_canvas_click)

        self.cell_rect_ids: List[int] = []
        self.cell_text_ids: List[int] = []

        self.default_bg = "#dddddd"
        self.x_classical_bg = "#c9daf8"
        self.o_classical_bg = "#f4cccc"

        self.x_fg = "#0b5394"
        self.o_fg = "#990000"
        self.mixed_fg = "#674ea7"

        self.classical_font = ("Arial", int(12 * self.scale), "bold")
        self.spooky_font = ("Arial", int(10 * self.scale))

        for idx in range(9):
            r, c = divmod(idx, 3)
            x0 = c * self.cell_size + self.margin
            y0 = r * self.cell_size + self.margin
            x1 = (c + 1) * self.cell_size - self.margin
            y1 = (r + 1) * self.cell_size - self.margin

            rect = self.board_canvas.create_rectangle(
                x0, y0, x1, y1,
                fill=self.default_bg,
                outline="",
                width=0
            )
            self.cell_rect_ids.append(rect)

            height = (y1 - y0)
            text_y = y0 + height * 0.35

            text = self.board_canvas.create_text(
                (x0 + x1) / 2,
                text_y,
                text="",
                font=self.spooky_font,
                fill="black",
            )
            self.cell_text_ids.append(text)

        for i in range(1, 3):
            x = i * self.cell_size
            w = max(1, int(2 * self.scale))
            self.board_canvas.create_line(x, 0, x, self.canvas_size, width=w)
            self.board_canvas.create_line(0, x, self.canvas_size, x, width=w)

        self.line_ids: List[int] = []
        self.highlight_color = "#000000"
        self.highlight_width = max(1, int(3 * self.scale))

        btn_font = ("Arial", int(10 * self.scale))
        reset_btn = tk.Button(root, text="New Game",
                              command=self.reset_game,
                              font=btn_font)
        reset_btn.grid(row=2, column=0, pady=int(5 * self.scale))

        self.quantum_button = tk.Button(
            root,
            text="Quantum collapse",
            command=self.quantum_collapse_current_move,
            font=btn_font,
        )
        self.quantum_button.grid(row=3, column=0, pady=int(3 * self.scale))

        self.temp_first_cell: Optional[int] = None

        self.update_status()
        self.update_board_display()

    def cell_center(self, idx: int) -> Tuple[float, float]:
        """Return pixel center of cell index 0..8."""
        r, c = divmod(idx, 3)
        x0 = c * self.cell_size + self.margin
        y0 = r * self.cell_size + self.margin
        x1 = (c + 1) * self.cell_size - self.margin
        y1 = (r + 1) * self.cell_size - self.margin
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    def reset_game(self):
        self.logic.reset()
        self.temp_first_cell = None
        self.update_board_display()
        self.update_status()

    def update_status(self):
        if self.logic.mode == 'PLAY':
            if self.temp_first_cell is None:
                self.status_var.set(
                    f"{self.logic.current_player}'s turn: choose first square of spooky pair"
                )
            else:
                self.status_var.set(
                    f"{self.logic.current_player}'s turn: choose second square (must be different)"
                )
        else:
            if self.logic.collapse_index < len(self.logic.collapse_moves):
                mv = self.logic.collapse_moves[self.logic.collapse_index]
                a, b = mv.cells
                self.status_var.set(
                    f"Collapse phase: Player {self.logic.collapse_chooser} chooses "
                    f"collapse for {mv.player}{mv.index} (squares {a+1} and {b+1})"
                )
            else:
                self.status_var.set("Collapse phase: finishing...")

    def update_board_display(self):
        """Re-render cell texts, colors, and spooky lines from Logic state."""
        cell_texts = [[] for _ in range(9)]
        players_in_cell = [set() for _ in range(9)]

        for i in range(9):
            cb = self.logic.collapsed_board[i]
            if cb is not None:
                p, idx = cb
                cell_texts[i].append(f"{p}({idx})")
                players_in_cell[i].add(p)

        for m in self.logic.moves:
            label = f"{m.player}{m.index}"
            a, b = m.cells
            cell_texts[a].append(label)
            cell_texts[b].append(label)
            players_in_cell[a].add(m.player)
            players_in_cell[b].add(m.player)

        if self.logic.mode == 'COLLAPSE':
            for m in self.logic.collapse_moves:
                if m.collapsed_to is None:
                    label = f"{m.player}{m.index}"
                    a, b = m.cells
                    cell_texts[a].append(label)
                    cell_texts[b].append(label)
                    players_in_cell[a].add(m.player)
                    players_in_cell[b].add(m.player)

        for i in range(9):
            label = "\n".join(cell_texts[i])
            cb = self.logic.collapsed_board[i]
            pset = players_in_cell[i]

            bg = self.default_bg
            fg = "black"
            font = self.spooky_font
            outline = ""
            outline_width = 0

            if cb is not None:
                p, _ = cb
                if p == 'X':
                    bg = self.x_classical_bg
                    fg = self.x_fg
                else:
                    bg = self.o_classical_bg
                    fg = self.o_fg
                font = self.classical_font
            else:
                if "X" in pset and "O" not in pset:
                    fg = self.x_fg
                elif "O" in pset and "X" not in pset:
                    fg = self.o_fg
                elif "X" in pset and "O" in pset:
                    fg = self.mixed_fg

                if (
                    self.logic.mode == 'PLAY'
                    and self.temp_first_cell is not None
                    and i == self.temp_first_cell
                ):
                    outline = self.highlight_color
                    outline_width = self.highlight_width

            self.board_canvas.itemconfig(
                self.cell_rect_ids[i],
                fill=bg,
                outline=outline,
                width=outline_width,
            )
            self.board_canvas.itemconfig(
                self.cell_text_ids[i],
                text=label,
                fill=fg,
                font=font,
            )

        self.redraw_lines()

    def redraw_lines(self):
        """Draw colored lines for all spooky pairs."""
        for lid in self.line_ids:
            self.board_canvas.delete(lid)
        self.line_ids = []

        def add_line(a: int, b: int, player: str):
            x1, y1 = self.cell_center(a)
            x2, y2 = self.cell_center(b)
            color = self.x_fg if player == 'X' else self.o_fg
            w = max(1, int(2 * self.scale))
            self.line_ids.append(
                self.board_canvas.create_line(x1, y1, x2, y2, fill=color, width=w)
            )

        for m in self.logic.moves:
            add_line(m.cells[0], m.cells[1], m.player)

        if self.logic.mode == 'COLLAPSE':
            for m in self.logic.collapse_moves:
                if m.collapsed_to is None:
                    add_line(m.cells[0], m.cells[1], m.player)

        for text_id in self.cell_text_ids:
            self.board_canvas.tag_raise(text_id)

    def on_canvas_click(self, event):
        """Map a mouse click on the canvas to a cell index and delegate."""
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        if 0 <= col < 3 and 0 <= row < 3:
            idx = int(row * 3 + col)
            self.on_cell_click(idx)

    def on_cell_click(self, idx: int):
        if self.logic.mode == 'PLAY':
            self.handle_play_click(idx)
        else:
            self.handle_collapse_click(idx)

    def handle_play_click(self, idx: int):
        if self.logic.collapsed_board[idx] is not None:
            messagebox.showinfo("Illegal move", "Occupied!")
            return

        if self.temp_first_cell is None:
            self.temp_first_cell = idx
            self.update_board_display()
            self.update_status()
        else:
            if idx == self.temp_first_cell:
                messagebox.showinfo("Illegal move", "Must be different.")
                return

            cell1, cell2 = self.temp_first_cell, idx

            self.logic.add_spooky_move(cell1, cell2)

            self.temp_first_cell = None
            self.update_board_display()
            self.update_status()

            if self.logic.mode == 'COLLAPSE':
                messagebox.showinfo(
                    "Loop detected",
                    f"Player {self.logic.cycle_creator} created a loop.\n"
                    f"Player {self.logic.collapse_chooser} will choose how to collapse.",
                )

    def handle_collapse_click(self, idx: int):
        if self.logic.collapse_index >= len(self.logic.collapse_moves):
            return

        mv = self.logic.collapse_moves[self.logic.collapse_index]

        if idx not in mv.cells:
            messagebox.showinfo(
                "Invalid choice",
                "You must choose one of the two squares for this spooky marker."
            )
            return

        if self.logic.collapsed_board[idx] is not None:
            messagebox.showinfo(
                "Invalid choice",
                "This square is already occupied by a collapsed marker. "
                "Choose the other one."
            )
            return

        accepted = self.logic.collapse_step(idx)
        if not accepted:
            return

        self.update_board_display()
        self.update_status()

        if self.logic.mode == 'PLAY':
            self.announce_result_if_any()

    def announce_result_if_any(self):
        """Check for a winner and show a messagebox if the game ended."""
        result = self.logic.check_winner()
        if result is None:
            return

        if result[0] == 'DRAW':
            messagebox.showinfo(
                "Result",
                f"Game over: draw (equal minimal index sum = {result[2]}).",
            )
        else:
            winner = result[0]
            if len(result) == 3:
                _, line, s = result
                messagebox.showinfo(
                    "Winner",
                    f"Player {winner} wins!\n"
                    f"Winning line: {tuple(i+1 for i in line)}, "
                    f"sum of indices = {s}.",
                )
            else:
                _, line, s, (other, o_line, o_s) = result
                messagebox.showinfo(
                    "Winner",
                    f"Both players formed three in a row.\n"
                    f"Player {winner} wins with smaller index sum {s} "
                    f"vs {other}'s {o_s}.",
                )

    def quantum_collapse_current_move(self):
        """
        Use a real quantum 'coin flip' to choose how the current spooky move
        collapses: 0 -> first square, 1 -> second square.
        """
        if self.logic.mode != 'COLLAPSE':
            messagebox.showinfo(
                "Not in collapse phase",
                "Quantum collapse is only available during a collapse."
            )
            return

        if self.logic.collapse_index >= len(self.logic.collapse_moves):
            return

        mv = self.logic.collapse_moves[self.logic.collapse_index]
        a, b = mv.cells

        self.status_var.set(
            f"Quantum collapse: contacting IBM backend for {mv.player}{mv.index}..."
        )
        self.root.update_idletasks()

        try:
            bit = self.quantum_coin.flip()
        except Exception as e:
            messagebox.showerror(
                "Quantum error",
                f"Error contacting quantum backend:\n{e}\n\n"
                "Try again or use a classical collapse."
            )
            self.update_status()
            return

        chosen_cell = a if bit == 0 else b
        if self.logic.collapsed_board[chosen_cell] is not None:
            other = b if chosen_cell == a else a
            if self.logic.collapsed_board[other] is not None:
                messagebox.showinfo(
                    "Already collapsed",
                    "Both squares for this move are already occupied."
                )
                self.update_status()
                return
            chosen_cell = other

        which = "first" if chosen_cell == a else "second"
        self.status_var.set(
            f"Quantum collapse result: measured {bit}, "
            f"{mv.player}{mv.index} → {which} square (cell {chosen_cell+1})."
        )
        self.root.update_idletasks()

        accepted = self.logic.collapse_step(chosen_cell)
        if not accepted:
            messagebox.showinfo("Collapse failed", "Could not apply quantum collapse.")
            self.update_status()
            return

        self.update_board_display()
        self.update_status()

        if self.logic.mode == 'PLAY':
            self.announce_result_if_any()

    def on_close(self):
        """
        Called when the window is closed (X button).
        Try to clean up quantum resources, then shut down Tk and exit.
        """
        try:
            qc = getattr(self, "quantum_coin", None)
            if qc is not None:
                for attr in ("close", "disconnect", "shutdown"):
                    if hasattr(qc, attr):
                        getattr(qc, attr)()
                        break
        except Exception:
            pass

        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

        sys.exit(0)

   




if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-aer",
        action="store_true",
        help="Skip hardware and use Aer simulator only",
    )
    args = parser.parse_args()

    root = tk.Tk()

    root.update_idletasks()
    base_height = 900
    screen_h = root.winfo_screenheight()
    auto_scale = max(1.0, min(2.5, screen_h / base_height))

    app = QuantumTicTacToeGUI(root, scale=auto_scale, force_aer=args.force_aer)

    root.protocol("WM_DELETE_WINDOW", app.on_close)

    root.mainloop()