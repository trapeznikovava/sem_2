define res_len /* gamma_len */;
define init_steps /* init_steps */;

__in bit key[128];
__in bit iv[96];

bit LFSR[128];
bit NFSR[128];

__out bit result[res_len];

void shift_LFSR()
{
    __mem bit f = LFSR[0]^LFSR[7]^LFSR[38]^LFSR[70]^LFSR[81]^LFSR[96];
    int i;
    for(i = 0; i < 127; i = i + 1)
    {
        LFSR[i] = LFSR[i + 1];
    }
    LFSR[127] = f;
}

void shift_NFSR()
{
    __mem bit g1 = LFSR[0]^NFSR[0]^NFSR[26]^NFSR[56]^NFSR[91]^NFSR[96];
    __mem bit g2 = NFSR[3]&NFSR[67]^NFSR[11]&NFSR[13]^NFSR[17]&NFSR[18];
    __mem bit g3 = NFSR[27]&NFSR[59]^NFSR[40]&NFSR[48]^NFSR[61]&NFSR[65];
    bit g4 = NFSR[68]&NFSR[84];
    __mem bit g = g1^g2^g3^g4;
    int i;
    for (i = 0; i < 127; i = i + 1)
    {
        NFSR[i] = NFSR[i + 1];
    }
    NFSR[127] = g;
}

bit h(bit x0, bit x1, bit x2, bit x3, bit x4, bit x5, bit x6, bit x7, bit x8)
{
    return x0&x1 ^ x2&x3 ^ x4&x5 ^ x6&x7 ^ x0&x4&x8;
}

void set_key_iv()
{
    int i;
    for (i = 0; i < 128; i = i + 1)
    {
        NFSR[i] = key[i];
    }
    for (i = 0; i < 96; i = i + 1)
    {
        LFSR[i] = iv[i];
    }
    for (i = 96; i < 128; i = i + 1)
    {
        LFSR[i] = 1;
    }
}

void main()
{
    set_key_iv();
    int i;
    for (i = 0; i < init_steps; i = i + 1)
    {
        __mem bit mask = LFSR[93]^NFSR[2]^NFSR[15]^NFSR[36]^NFSR[45]^NFSR[64]^NFSR[73]^NFSR[89];
        bit output = mask ^ h(NFSR[12],LFSR[8],LFSR[13],LFSR[20],NFSR[95],LFSR[42],LFSR[60],LFSR[79],LFSR[95]);
        shift_NFSR();
        shift_LFSR();
        LFSR[127] = LFSR[127] ^ output;
        NFSR[127] = NFSR[127] ^ output;
    }
    for (i = 0; i < res_len; i = i + 1)
    {
        __mem bit mask = LFSR[93]^NFSR[2]^NFSR[15]^NFSR[36]^NFSR[45]^NFSR[64]^NFSR[73]^NFSR[89];
        result[i] = mask ^ h(NFSR[12],LFSR[8],LFSR[13],LFSR[20],NFSR[95],LFSR[42],LFSR[60],LFSR[79],LFSR[95]);
        shift_NFSR();
        shift_LFSR();
    }
}