# Resume and interview material

## 中文项目名称

**WavePilot：自适应声学OFDM软件调制解调器**

## 中文简历表述

- 独立设计端到端OFDM文件传输链路，实现重复半帧同步、载波频偏估计与补偿、长训练序列信道估计、频域单抽头均衡和导频公共相位跟踪。
- 实现Gray编码QPSK/16QAM/64QAM、max-log软解调及约束长度7卷积码软判决Viterbi译码，通过32位CRC完成文件级端到端正确性验证。
- 构建48 kHz、12 kHz载波的单声道PCM WAV声学传输路径，以及包含AWGN、多径、定时偏移、频偏和突发噪声的确定性信道模型。
- 设计以目标BLER、EWMA SNR/BLER与迟滞为依据的可解释MCS策略，并通过自动SNR扫描量化BLER、EVM与有效吞吐率权衡。

可直接使用的验证数据：

> 在256字节、五次重复的软件多径信道实验中，QPSK与16QAM在8 dB达到0 BLER；64QAM在12 dB取得约14.36 kb/s offered rate、20% BLER和约11.48 kb/s goodput。

必须注明这是**确定性软件信道实验**，不能写成真实无线或声学距离测试。

## English resume bullets

- Built an end-to-end OFDM file modem with repeated-half synchronization, CFO estimation/correction, long-training channel estimation, one-tap equalization and pilot common-phase tracking.
- Implemented Gray QPSK/16QAM/64QAM, max-log soft demapping and a K=7 soft Viterbi decoder, with file-level CRC-32 verification.
- Added a 48 kHz real-passband PCM WAV path and deterministic AWGN, multipath, timing, CFO and burst-noise channel models.
- Designed an explainable target-BLER link adapter and automated sweeps for BLER, EVM, CFO error, offered rate and delivered goodput.

## Interview prompts

Be ready to explain:

1. Why repeated halves reveal CFO and what limits the unambiguous range.
2. Why the cyclic prefix converts multipath equalization into one complex division per carrier.
3. Why two repeated headers are combined as LLRs instead of hard-vote bits.
4. Why 64QAM can have higher offered rate but worse goodput.
5. How Gray labeling changes the cost of a nearest-neighbor symbol error.
6. Why decision-directed EVM is optimistic at low SNR.
7. What sample-rate offset does to pilot phase across time and frequency.
8. Which blocks should move to C++ or FPGA first and how bit-exact tests would be built.

