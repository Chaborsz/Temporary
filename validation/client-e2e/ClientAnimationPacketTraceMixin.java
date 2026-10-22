package validation.mixin;

import dev.companion.minecraft.CompanionEntity;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayNetworkHandler;
import net.minecraft.network.packet.s2c.play.EntityAnimationS2CPacket;
import net.minecraft.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** CI-only probe at the mapped 1.20.1 animation-packet receive boundary. */
@Mixin(ClientPlayNetworkHandler.class)
abstract class ClientAnimationPacketTraceMixin {
    @Inject(method = "onEntityAnimation(Lnet/minecraft/network/packet/s2c/play/EntityAnimationS2CPacket;)V", at = @At("HEAD"))
    private void ci$beforeEntityAnimation(EntityAnimationS2CPacket packet, CallbackInfo ci) {
        MinecraftClient client = MinecraftClient.getInstance();
        Entity entity = client.world == null ? null : client.world.getEntityById(packet.getId());
        if (entity instanceof CompanionEntity companion) {
            validation.CiClientValidation.trace("CI_SWING_PACKET_RECEIVED side=CLIENT thread="
                    + Thread.currentThread().getName() + " animationId=" + packet.getAnimationId()
                    + " entityId=" + companion.getId() + " uuid=" + companion.getUuid()
                    + " class=" + companion.getClass().getName() + " age=" + companion.age
                    + " beforeSwinging=" + companion.handSwinging
                    + " beforeTicks=" + companion.handSwingTicks
                    + " beforeHand=" + companion.preferredHand);
    }
}
