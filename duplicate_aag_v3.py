import math
import sys

class EncodingDuplication:
    max_instances = 10
    
    def __init__(self, filename, gamma_num, key_len, rep_flag):

        self.filename = filename
        self.gamma_num = gamma_num
        self.key_len = key_len
        self.rep_flag = rep_flag
        self.rep_interval = [
            [i, min(i + self.max_instances, gamma_num)]
            for i in range(0, gamma_num, self.max_instances)
        ]
        self.rep_st = self.rep_interval[rep_flag][0]
        self.rep_end = self.rep_interval[rep_flag][1]
        self.iv_len = None
        self.val_num = None
        self.out_len = None

        self.output_vars_basic_list = []
        self.encoding_lines = []

        with open(self.filename, 'r', encoding='utf-8') as f:
            for line in f:
                if line != "":
                    self.encoding_lines.append(line)

    def shift_variable(self, a, rep):
        if a // 2 <= self.key_len:
            return str(a)
        elif a // 2 <= self.key_len + self.iv_len:
            return str(a + 2 * rep * self.iv_len)
        else:
            return str(
                2 * (self.key_len + self.iv_len * self.gamma_num) 
                + (a - 2 * (self.key_len + self.iv_len)) 
                + 2 * rep * (self.val_num - self.key_len - self.iv_len)
            )

    def new_equation(self, x, y, z, rep):
        ans=""
        ans += self.shift_variable(x, rep) + " "
        ans += self.shift_variable(y, rep) + " "
        ans += self.shift_variable(z, rep) + "\n"

        return ans

    def print_encoding(self, output_filename : str):
        ans = []
        content = self.encoding_lines[0].split()
        
        self.val_num = int(content[1])  # число изначальных переменных
        self.iv_len = int(content[2]) - self.key_len

        #чтение номеров изначальных выходных переменных
        for i in range(int(content[4])):
            output_var = int(self.encoding_lines[1 + self.key_len + self.iv_len + i])
            self.output_vars_basic_list.append(output_var)
    
        self.out_len = len(self.output_vars_basic_list)
        
        if self.rep_flag == 0:
            #запись заголовка
            ans.append("aag ")
            ans.append(str((int(content[1])-self.key_len)*self.gamma_num+self.key_len) + " ")
            ans.append(str(self.key_len + self.iv_len*self.gamma_num) + " ")
            ans.append("0 ")
            ans.append(str(int(content[4])*self.gamma_num)+" ")
            ans.append(str(int(content[5])*self.gamma_num)+"\n")

            #запись новых входных переменных
            for i in range(2,int(ans[2])*2+1,2):
                ans.append(str(i)+"\n")

            #запись новых выходных переменных
            for rep in range(self.gamma_num):
                for x in self.output_vars_basic_list:
                    out_var = self.shift_variable(x, rep)
                    ans.append(str(out_var) + '\n')


        equations = self.encoding_lines[1 + self.key_len + self.iv_len + self.out_len:]
        equations = list(map(lambda x: x.split(), equations))
        
        for rep in range(self.rep_st, self.rep_end):
            for i in range(len(equations)):
                ans.append(self.new_equation(int(equations[i][0]),int(equations[i][1]),int(equations[i][2]),rep))
        
        mode = 'w' if self.rep_flag == 0 else 'a'
        with open(output_filename, mode) as fout:
            for s in ans:
                fout.write(s)


def make_duplicate(filename, out_file, key_len, gamma_num):

    calls_num = math.ceil(gamma_num / EncodingDuplication.max_instances)
    
    for i in range(calls_num):
        rep_flag = i
        enc_dup = EncodingDuplication(filename, gamma_num, key_len, rep_flag)
        # print(*enc_dup.rep_interval, sep='\n')
        enc_dup.print_encoding(out_file)


if __name__ == "__main__":
    filename = sys.argv[1]
    out_file = sys.argv[2]
    key_len = int(sys.argv[3])
    gamma_num = int(sys.argv[4])
    make_duplicate(filename, out_file, key_len, gamma_num)
