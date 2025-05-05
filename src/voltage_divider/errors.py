class NoPrecisionSatisfiesConstraintsError(Exception):
    """No Precision Series can meet the outlined requirements."""
    def __init__(self, guesses, table):
        self.guesses = guesses  # [float, float]
        self.table = table      # List of (compliant: bool, precision: float, vout: object)
        super().__init__(self.__str__())

    def __str__(self):
        msg = ["No Precision Series can meet the outlined requirements\n"]
        msg.append(f"Initial Guess: r-hi={self.guesses[0]}  r-lo={self.guesses[1]}")
        msg.append("Precision    Vout:")
        for elem in self.table:
            msg.append(f"{elem[1]}           {elem[2]}")
        return "\n".join(msg)

class VinRangeTooLargeError(Exception):
    """V-in Range is too large - No solution can be found."""
    def __init__(self, guesses, vin_screen):
        self.guesses = guesses  # [float, float]
        self.vin_screen = vin_screen
        super().__init__(self.__str__())

    def __str__(self):
        msg = ["V-in Range is too large - No solution can be found\n"]
        msg.append(f"Initial Guess: r-hi={self.guesses[0]}  r-lo={self.guesses[1]}")
        msg.append(f"Vout for Vin with perfect resistors: {self.vin_screen}")
        return "\n".join(msg)

class IncompatibleVinVoutError(Exception):
    """Incompatible V-in and V-out Constraints Encountered."""
    def __init__(self, v_in, v_out):
        self.v_in = v_in
        self.v_out = v_out
        super().__init__(self.__str__())

    def __str__(self):
        msg = ["Incompatible V-in and V-out Constraints Encountered\n"]
        msg.append(f"V-in: {self.v_in}  V-out: {self.v_out}")
        return "\n".join(msg)

class NoSolutionFoundError(Exception):
    """Failed to find a voltage divider solution that meets the provided requirements."""
    def __init__(self, msg):
        self.msg = msg
        super().__init__(self.__str__())

    def __str__(self):
        return f"Failed to find a voltage divider solution that meets the provided requirements: {self.msg}" 
