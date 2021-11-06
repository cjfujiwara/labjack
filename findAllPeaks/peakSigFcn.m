function PeakSig = peakSigFcn(x, x_length)
%PEAKSIGFCN Summary of this function goes here
%   Detailed explanation goes here
base = 4*cos(2*pi*x);

Pos = [1 2 3 5 7 8]/10;
Hgt = [3 7 5 5 4 5];
Wdt = [1 3 3 4 2 3]/100;

lengthPos = length(Pos);
Gauss = zeros(lengthPos, x_length);
for n = 1:lengthPos
    Gauss(n,:) =  2 + Hgt(n)*exp(-((x - Pos(n))/Wdt(n)).^2);
end

PeakSig = sum(Gauss)+base;

