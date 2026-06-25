import sys
from itertools import combinations

class AigerTransformer():
    def __init__(self, filename, gamma_num, keylen, ivlen):
        self.in_file = filename
        self.gamma_num = gamma_num
        self.keylen = keylen
        self.ivlen = ivlen
        self.input_vars = []
        self.out_vars = []
        self.gates = []
        self.vars_cnt = 0
        self.output_vars_cnt = 0
        self.gates_count = 0
    
    def get_ivs_bits(self, strategy: str):
        ivs_comb = []

        if strategy == 'hamming':
            hamming_weight = 0

            while len(ivs_comb) < self.gamma_num:
                ivs_comb += list(combinations(range(self.ivlen), hamming_weight))
                hamming_weight += 1
        else:
            raise NotImplementedError

        ivs = []

        for indices in ivs_comb[:self.gamma_num]:
            iv = [1 if i in indices else 0 for i in range(self.ivlen)]
            ivs.append(iv)

        t = []

        for i in range(self.gamma_num):
            t = t + ivs[i]
        
        return t

    def read_header(self, line):
        header = line.split()
        self.vars_cnt = int(header[1])
        self.output_vars_cnt = int(header[4])
        self.gates_count = int(header[5])

    def print_header(self, fout):
        fout.write(f"aag {self.vars_cnt} {self.keylen} 0 {self.output_vars_cnt} {self.gates_count+self.ivlen*self.gamma_num}\n")
    
    def read_input(self, line):
        var_num = int(line)
        self.input_vars.append(var_num)
    
    def print_input(self, fout):
        for i in range(self.keylen):
            fout.write(f"{self.input_vars[i]}\n")

    def read_output(self, line):
        var_num = int(line)
        self.out_vars.append(var_num)
    
    def print_output(self, fout):
        for var_num in self.out_vars:
            fout.write(f"{var_num}\n")

    def read_gate(self, line):
        self.gates.append(list(map(int, line.strip().split())))


    def print_gates(self, fout, ivs_bits):
        for i in range(self.keylen, self.keylen+self.ivlen*self.gamma_num):
            fout.write(f"{self.input_vars[i]} {ivs_bits[i - self.keylen]} {ivs_bits[i - self.keylen]}\n")
        for gate in self.gates:
            fout.write(f"{gate[0]} {gate[1]} {gate[2]}\n")

    def print_transformed_encoding(self, out_file: str, strategy: str):
        """
        вывод в файл кодировки, в которой вектора инициализации
        означены в соответствии с заданной стратегией
        """

        ivs_bits = self.get_ivs_bits(strategy)
        ivslen = self.ivlen * self.gamma_num
        null = 0
        unit = 1
        gates = []
        

        with open(self.in_file, 'r') as fin:
            header_flag = True
            input_lines_cnt = self.keylen + ivslen
            output_lines_cnt = None

            for line in fin:
                if line == '':
                    continue
            
                if header_flag:
                    header_flag = False
                    self.read_header(line)
                    output_lines_cnt = self.output_vars_cnt
                    continue
                
                if input_lines_cnt > 0:
                    self.read_input(line)
                    input_lines_cnt -= 1
                    continue

                if output_lines_cnt > 0:
                    self.read_output(line)
                    output_lines_cnt -= 1
                    continue
                

                gates = self.read_gate(line)
            
            fout = open(out_file, 'w')
            self.print_header(fout)
            self.print_input(fout)
            self.print_output(fout)
            self.print_gates(fout, ivs_bits)

def define_gates(filename, out_file, keylen, gamma_num, ivlen):
    aiger = AigerTransformer(filename, gamma_num, keylen, ivlen)
    aiger.print_transformed_encoding(out_file, "hamming")


if __name__ == "__main__":
    filename = sys.argv[1]
    out_file = sys.argv[2]
    keylen = int(sys.argv[3])
    gamma_num = int(sys.argv[4])
    ivlen = int(sys.argv[5])
    define_gates(filename, out_file, keylen, gamma_num, ivlen)


        #     vars_cnt = int(header[0])
        #     input_vars_cnt = self.keylen
        #     output_vars_cnt = int(header[3])
        #     outlen = output_vars_cnt
        #     gates_cnt = int(header[4]) + ivslen

        #     out_vars = [int(lines[keylen + ivslen + x][0]) for x in range(1, output_vars_cnt + 1)]

        #     for x in range(keylen + 1, keylen + ivslen + 1):
        #         gates.append([2 * x, null, null] if t[x - keylen - 1] == 0 else [2 * x, unit, unit])

        #     for line in lines[keylen + ivslen + outlen + 1:]:
        #         x = list(map(int, line))
        #         gates.append(x)

        # print(f'aag {vars_cnt} {keylen} 0 {outlen} {gates_cnt}')

        # for i in range(1, keylen + 1):
        #     print(2 * i)

        # for x in out_vars:
        #     print(x)

        # for g in gates:
        #     print(*g, sep=' ', end='\n')
